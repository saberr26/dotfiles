// A simple pseudo-random number generator
float rand(vec2 co){
    return fract(sin(dot(co.xy, vec2(12.9898, 78.233))) * 43758.5453);
}

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 uv = fragCoord.xy / iResolution.xy;

    // --- 1. Chromatic Aberration ---
    // A lens distortion effect common in futuristic UIs.
    // Gives a slight red/blue fringe at the edges of text.
    float aberration = 0.0015;
    vec3 termColor;
    termColor.r = texture(iChannel0, uv + vec2(aberration, 0.0)).r;
    termColor.g = texture(iChannel0, uv).g;
    termColor.b = texture(iChannel0, uv - vec2(aberration, 0.0)).b;
    float alpha = texture(iChannel0, uv).a;

    // --- 2. Text "Bit Shimmer" ---
    // Makes parts of the text randomly flicker with a highlight color.
    float shimmer = rand(uv + floor(iTime * 20.0));
    if (shimmer > 0.99) { // Only affect a tiny fraction of pixels each frame
        termColor.rgb += vec3(0.5, 1.0, 0.8); // Add a bright aqua highlight
    }

    // --- 3. Background Particle Stream ---
    // Creates a field of particles that drift upwards.
    vec2 p_uv = uv * vec2(1.0, 2.0); // Stretch the y-axis
    float speed = iTime * 0.2;
    float particles = rand(floor(p_uv * 200.0) / 200.0 - speed);
    particles = pow(particles, 20.0) * 0.5; // Make particles sparse and sharp
    vec3 backgroundColor = vec3(particles * 0.5, particles, particles * 0.8);

    // --- 4. Combine everything ---
    // Blend the shimmering text onto the particle background.
    vec3 finalColor = mix(backgroundColor, termColor, alpha);

    fragColor = vec4(finalColor, 1.0);
}
