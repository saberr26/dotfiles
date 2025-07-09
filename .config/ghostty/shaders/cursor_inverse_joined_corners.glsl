
/* cursor_smear_advanced.glsl
 *
 * Trail-and-tween shader for Ghostty / Shadertoy wrapper.
 * -  “Corner-aware” trail: always joins the *matched* corners of the
 *    origin and destination rectangles, so the bar is flush with the
 *    cursor edges whatever the motion vector.
 * -  Tweened cursor: the solid block travels from the old position to
 *    the new one over `DURATION`, so the real cursor can be hidden or
 *    outlined while the fake block animates.
 * -  Simple “mass” illusion: the trail tapers as the block decelerates
 *    (ease-out), and alpha falls off with distance from the head.
 *
 * Plug this file into the `ghostty_wrapper.glsl` where `$REPLACE$`
 * lives, rebuild, and test.
 */

/* ------------------------------------------------------------------ *
 *  Helpers                                                           *
 * ------------------------------------------------------------------ */

float easeOutCubic(float t) {
    return 1.0 - pow(1.0 - t, 3.0);
}

/* convert {pixel → NDC}, keeping –1‥+1 horizontally and aspect-correct
   vertically (Ghostty’s “top-left origin” comes in via fragCoord).     */
vec2 ndc(vec2 frag, float isPos) {
    return (frag * 2.0 - iResolution.xy * isPos) / iResolution.y;
}

/* SDF for rectangle centred on `xy` with half-extents `b`. ---------- */
float sdBox(vec2 p, vec2 xy, vec2 b) {
    vec2 d = abs(p - xy) - b;
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);
}

/* Signed distance to a general parallelogram defined by its 4 vertices. */
float sdParallelogram(vec2 p, vec2 v0, vec2 v1, vec2 v2, vec2 v3) {
    float signAcc = 1.0; // winding
    float distSq = dot(p - v0, p - v0); // initialise with v0

    // Inline edge helper ------------------------------------------------
    #define EDGE(A,B) {                                                   \
                        vec2 e = B - A;                                                   \
                        vec2 w = p - A;                                                   \
                        vec2 proj = A + e * clamp(dot(w,e)/dot(e,e), 0.0, 1.0);           \
                        distSq = min(distSq, dot(p-proj, p-proj));                        \
                        float c0 = step(0.0, p.y - A.y);                                  \
                        float c1 = 1.0 - step(0.0, p.y - B.y);                            \
                        float c2 = 1.0 - step(0.0, e.x*w.y - e.y*w.x);                    \
                        float flip = mix(1.0, -1.0, step(0.5, c0*c1*c2 +                  \
                                                             (1.0-c0)*(1.0-c1)*(1.0-c2)));\
                        signAcc *= flip;                                                  \
                    }
    EDGE(v0, v3)
    EDGE(v3, v2)
    EDGE(v2, v1)
    EDGE(v1, v0)
    #undef EDGE

    return signAcc * sqrt(distSq);
}

/* Fast anti-alias helper – linearly scales over 2 logical pixels. */
float aa(float d) {
    return 1.0 - smoothstep(0.0, ndc(vec2(2.0), 0.0).x, d);
}

/* Pick which two *vertical* sides map to which corners depending on the
   motion vector.  We want the trail always to hug the true swept area.  */
void matchedCorners(
    vec4 cursor, // xywh (NDC) of the *new* cursor
    vec4 cursorPrev, // xywh (NDC) of the *old* cursor
    out vec2 A0, out vec2 B0, // top/bot corners  (origin)
    out vec2 A1, out vec2 B1) // top/bot corners  (destination)
{
    vec2 dir = cursor.xy - cursorPrev.xy; // motion vector
    // Screen Y runs *down* after ndc(): up == –ve   --------------------
    bool moveRight = dir.x >= 0.0;
    bool moveDown = dir.y >= 0.0;

    // Choose leading and trailing sides based on dominant axes.  -------
    // Horizontal motion ⇒ use LEFT or RIGHT edges; vertical ⇒ TOP/BOT.
    bool horizDominant = abs(dir.x) >= abs(dir.y);

    if (horizDominant) {
        /* use the vertical edges whose normal faces travel direction   */
        float xLead = moveRight ? cursorPrev.x + cursorPrev.z // right side
            : cursorPrev.x; // left side
        float xTrail = moveRight ? cursor.x // left side
            : cursor.x + cursor.z; // right side

        // top-left, bottom-left (origin) ------------------------------
        A0 = vec2(xLead, cursorPrev.y);
        B0 = vec2(xLead, cursorPrev.y - cursorPrev.w);
        // top-right, bottom-right (dest) ------------------------------
        A1 = vec2(xTrail, cursor.y);
        B1 = vec2(xTrail, cursor.y - cursor.w);
    } else {
        /* vertical — use horizontal edges whose normal faces motion    */
        float yLead = moveDown ? cursorPrev.y - cursorPrev.w // bottom
            : cursorPrev.y; // top
        float yTrail = moveDown ? cursor.y // top
            : cursor.y - cursor.w; // bottom

        A0 = vec2(cursorPrev.x, yLead);
        B0 = vec2(cursorPrev.x + cursorPrev.z, yLead);
        A1 = vec2(cursor.x, yTrail);
        B1 = vec2(cursor.x + cursor.z, yTrail);
    }
}

/* ------------------------------------------------------------------ *
 *  Tunables                                                          *
 * ------------------------------------------------------------------ */

const vec4 COLOR_TRAIL = vec4(1.00, 0.73, 0.15, 1.0); // warm orange
const vec4 COLOR_TRAIL_EDGE = vec4(1.00, 0.20, 0.10, 1.0); // hot core
const float DURATION = 0.45; // seconds
const float THICKNESS_GAIN = 0.7; // taper factor

/* ------------------------------------------------------------------ *
 *  mainImage                                                         *
 * ------------------------------------------------------------------ */
void mainImage(out vec4 fragColor, in vec2 fragCoord)
{
    /* grab current frame buffer so our shader composes atop the text   */
    #if !defined(WEB)
    fragColor = texture(iChannel0, fragCoord / iResolution.xy);
    #endif

    vec2 px = ndc(fragCoord, 1.0);

    /* cursor rects: xy top-left, zw size – already passed by Ghostty   */
    vec4 cur = vec4(ndc(iCurrentCursor.xy, 1.0),
            ndc(iCurrentCursor.zw, 0.0));
    vec4 prv = vec4(ndc(iPreviousCursor.xy, 1.0),
            ndc(iPreviousCursor.zw, 0.0));

    /* animation progress --------------------------------------------- */
    float t = clamp((iTime - iTimeCursorChange) / DURATION, 0.0, 1.0);
    float prog = easeOutCubic(t);

    /* tweened cursor position (for the *travelling* block)             */
    vec2 tweenPos = mix(prv.xy, cur.xy, prog);
    vec4 tweenCur = vec4(tweenPos, cur.zw); // keep size

    /* choose matched corners & build parallelogram ------------------- */
    vec2 v0, v1, v2, v3; // old A0 B0 , new A1 B1 (naming later)
    matchedCorners(cur, prv, v0, v1, v2, v3);

    float dTrail = sdParallelogram(px, v0, v1, v2, v3);

    /* taper trail by thickness → simple scaling with (1-prog)         */
    float taper = mix(1.0, THICKNESS_GAIN, prog);
    dTrail /= taper;

    /* signed distance to tweened cursor rectangle -------------------- */
    vec2 center = tweenCur.xy - tweenCur.zw * vec2(-0.5, 0.5);
    float dCursor = sdBox(px, center, tweenCur.zw * 0.5);

    /* AA coverage ----------------------------------------------------- */
    float covTrail = aa(dTrail);
    float covEdge = aa(dTrail - 0.004); // inner core
    float covCursor = aa(dCursor);

    /* build colour ---------------------------------------------------- */
    vec4 col = fragColor;

    // hot inner edge, then softer outer
    col = mix(col, COLOR_TRAIL_EDGE, covEdge);
    col = mix(col, COLOR_TRAIL, covTrail * 0.6);

    // travelling block
    col = mix(col, COLOR_TRAIL, covCursor);

    // fade whole thing as the block finishes its journey
    float globalAlpha = 1.0 - prog; // 1 → 0
    fragColor = mix(fragColor, col, globalAlpha);
}
