void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 uv = fragCoord.xy / iResolution.xy;
    
    // --- 1. Background Grid & Scanlines ---
    // A subtle, moving grid to give a sense of a projection surface.
    // The sin(uv.y * ...) creates horizontal lines, the sin(uv.x * ...) creates vertical lines.
    float grid = sin(uv.y * 1000.0) * 0.01 + sin(uv.x * 500.0) * 0.01;
    vec3 backgroundColor = vec3(0.05, 0.1, 0.15) + grid; // Dark blue-cyan base

    // A sweeping vertical scanline to give the feeling of an active refresh.
    float scanline = abs(uv.x - fract(iTime * 0.1)) * 2.0;
    scanline = 1.0 - pow(scanline, 20.0) * 0.5; // pow makes the line sharp
    backgroundColor += vec3(0.1, 0.3, 0.4) * scanline;
    
    // --- 2. Get Terminal Color ---
    vec4 termColor = texture(iChannel0, uv);
    
    // --- 3. Text Glow (Bloom) ---
    // This makes the text look like it's emitting light.
    // We sample nearby pixels and add their brightness to the current pixel.
    vec3 glow = vec3(0.0);
    float glowSamples = 8.0; // More samples = smoother but potentially slower glow
    for (float i = -glowSamples; i < glowSamples; i += 2.0) {
        for (float j = -glowSamples; j < glowSamples; j += 2.0) {
            vec2 offset = vec2(i, j) / iResolution.xy * 1.5; // 1.5 is the glow radius
            glow += texture(iChannel0, uv + offset).rgb;
        }
    }
    glow /= pow(glowSamples, 2.0); // Average the samples
    
    // --- 4. Combine and Colorize ---
    // The final color is a mix of the terminal text and the glow,
    // all tinted with a futuristic cyan color.
    vec3 textColor = termColor.rgb + glow * 0.8;
    vec3 finalColor = mix(backgroundColor, textColor, termColor.a); // Use alpha to blend over background
    
    fragColor = vec4(finalColor, 1.0);
}
