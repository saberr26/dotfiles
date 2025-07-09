void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 uv = fragCoord.xy / iResolution.xy;

    // --- 1. Chromatic Aberration ---
    // Shifts the red and blue channels slightly for a color-fringe effect.
    float aberrationAmount = 0.003; // How much to shift colors.
    vec4 color;
    color.r = texture(iChannel0, uv - vec2(aberrationAmount, 0.0)).r;
    color.g = texture(iChannel0, uv).g;
    color.b = texture(iChannel0, uv + vec2(aberrationAmount, 0.0)).b;
    color.a = texture(iChannel0, uv).a;

    // --- 2. Phosphor Glow (Bloom) ---
    // Makes bright text appear to "bleed" or glow.
    float glowAmount = 4.0; // How wide the glow is.
    vec4 sum = vec4(0.0);
    int samples = 8;
    for (int i = -samples/2; i < samples/2; i++) {
        for (int j = -samples/2; j < samples/2; j++) {
            vec2 offset = vec2(i, j) / iResolution.xy * glowAmount;
            sum += texture(iChannel0, uv + offset);
        }
    }
    
    // Average the samples and add it to the original color.
    // The '0.1' controls the intensity of the glow.
    vec4 glow = sum / float(samples * samples) * 0.1; 
    
    fragColor = color + glow;
}
