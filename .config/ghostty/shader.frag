// 2D Random function for the starfield
float rand(vec2 st) {
    return fract(sin(dot(st.xy, vec2(12.9898,78.233))) * 43758.5453123);
}

void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    vec2 uv = (2.0 * fragCoord.xy - iResolution.xy) / iResolution.y; // Center coordinates
    vec2 uv_orig = uv;
    vec3 finalColor = vec3(0.0);

    // --- Gravitational Lensing ---
    // The closer to the center, the more we distort the coordinates
    float dist = length(uv);
    float lens_strength = 0.3;
    uv /= dist; // Normalize
    uv *= (dist - lens_strength / dist); // Apply inverse distortion

    // --- Background Starfield ---
    float stars = pow(rand(uv * 300.0), 20.0);
    finalColor += vec3(stars);

    // --- Accretion Disk ---
    // We use polar coordinates to create the disk
    float angle = atan(uv_orig.y, uv_orig.x);
    float radius = length(uv_orig);
    // Create noise that rotates around the center
    float disk_noise = fract(sin(angle * 10.0 + radius * 5.0 - iTime * 1.5) * 100.0);
    disk_noise = pow(disk_noise, 5.0); // Sharpen the noise
    // Define the disk's shape (a ring)
    float disk = smoothstep(0.4, 0.38, radius) * smoothstep(0.2, 0.22, radius);
    // Color the disk with hot orange/yellow tones
    vec3 disk_color = vec3(1.0, 0.5, 0.1) * disk_noise;
    finalColor += disk * disk_color;

    // --- Event Horizon (The Black Hole itself) ---
    float hole = 1.0 - smoothstep(0.2, 0.19, radius);
    finalColor *= hole;

    // --- Get Terminal Color ---
    vec4 termColor = texture(iChannel0, fragCoord.xy/iResolution.xy);
    finalColor = mix(finalColor, termColor.rgb, termColor.a);

    fragColor = vec4(finalColor, 1.0);
}
