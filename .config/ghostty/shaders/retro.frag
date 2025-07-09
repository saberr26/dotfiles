void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 uv = fragCoord.xy / iResolution.xy;
    vec4 termColor = texture(iChannel0, uv);

    // --- Convert to Monochrome ---
    // Calculate the brightness (luminance) of the original color.
    float brightness = dot(termColor.rgb, vec3(0.2126, 0.7152, 0.0722));

    // --- Apply Phosphor Color ---
    // The classic green color.
    vec3 phosphorColor = vec3(0.2, 1.0, 0.3);
    vec3 finalColor = brightness * phosphorColor;

    // --- Add Scanlines ---
    // Make every second line slightly darker to simulate a CRT grid.
    // Adjust 0.9 to make lines more or less intense.
    float scanline = mod(fragCoord.y, 2.0) * 0.1;
    finalColor -= scanline * finalColor;

    fragColor = vec4(finalColor, termColor.a);
}
