// A simple pseudo-random number generator
float rand(vec2 co){
    return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
}

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 uv = fragCoord.xy / iResolution.xy;
    vec4 termColor = texture(iChannel0, uv);

    // --- 1. Desaturate and cool the image ---
    // Make the colors colder and less vibrant, like an old monitor.
    float brightness = dot(termColor.rgb, vec3(0.2126, 0.7152, 0.0722));
    vec3 finalColor = vec3(brightness);
    finalColor *= vec3(0.8, 0.9, 1.1); // Tint towards blue/cyan

    // --- 2. Red Channel Bleed ---
    // In old TVs, bright reds would often "bleed" vertically.
    // We check if the original color was strongly red.
    if (termColor.r > 0.8 && termColor.g < 0.3 && termColor.b < 0.3) {
        // Mix in color from the pixels above and below to create a vertical smear
        float bleed = texture(iChannel0, uv + vec2(0.0, 0.005)).r;
        finalColor.r += bleed * 0.5;
        finalColor.g -= bleed * 0.2; // Staining other channels
        finalColor = clamp(finalColor, 0.0, 1.0);
    }
    
    // --- 3. Power Line Hum & Signal Interference ---
    // A combination of sine waves to simulate electrical interference.
    float hum = sin(uv.y * 300.0 + iTime * 2.0) * 0.02;
    hum += sin(uv.y * 10.0 - iTime) * 0.03;
    finalColor -= hum;

    // --- 4. VHS Static/Noise ---
    // A fine grain of noise over the whole image.
    float noise = (rand(uv + iTime) - 0.5) * 0.15;
    finalColor += noise;

    fragColor = vec4(finalColor, termColor.a);
}
