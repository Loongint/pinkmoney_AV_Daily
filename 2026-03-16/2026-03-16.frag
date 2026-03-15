#version 330
uniform float u_time;
in vec2 v_uv;
out vec4 fragColor;

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(
        mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
        mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
        u.y
    );
}

float eclipse(vec2 uv, float t) {
    vec2 moon_center = vec2(0.5, 0.5);
    vec2 shadow_center = moon_center + vec2(sin(t * 0.08) * 0.02, -0.015 + sin(t * 0.04) * 0.005);
    float moon_r = 0.22;
    float shadow_r = 0.20 + sin(t * 0.05) * 0.01;
    float transit = smoothstep(0.0, 12.0, t) * (1.0 - smoothstep(18.0, 30.0, t));
    vec2 offset = vec2(-0.18 + transit * 0.36, 0.0);
    float moon = length(uv - moon_center) - moon_r;
    float shadow = length(uv - (shadow_center + offset)) - shadow_r;
    float lit = smoothstep(-0.002, 0.002, moon) * smoothstep(0.002, -0.002, shadow);
    float penumbra = smoothstep(-0.045, 0.0, shadow) * (1.0 - smoothstep(0.0, 0.045, moon));
    return smoothstep(0.002, -0.002, moon) * (1.0 - lit * 0.97) - penumbra * 0.3;
}

float grid(vec2 uv, float scale, float thickness) {
    vec2 g = abs(fract(uv * scale) - 0.5);
    return 1.0 - smoothstep(thickness, thickness + 0.005, min(g.x, g.y));
}

void main() {
    vec2 uv = v_uv;
    float t = u_time;
    float aspect = 1920.0 / 1080.0;
    vec2 cuv = (uv - 0.5) * vec2(aspect, 1.0) + 0.5;

    float phase = t / 30.0;
    float silence = smoothstep(0.48, 0.52, phase) * (1.0 - smoothstep(0.62, 0.68, phase));

    float bg_n = noise(cuv * 3.5 + t * 0.015) * 0.5 + 0.5;
    float depth_n = noise(cuv * 1.2 + t * 0.008);
    vec3 void_color = vec3(0.02, 0.015, 0.04);
    vec3 deep_color = vec3(0.06, 0.045, 0.10);
    vec3 bg = mix(void_color, deep_color, depth_n * bg_n);

    float g1 = grid(cuv, 8.0, 0.008);
    float g2 = grid(cuv, 24.0, 0.003);
    float grid_fade = smoothstep(0.0, 8.0, t) * (1.0 - silence * 0.8);
    bg += g1 * 0.012 * grid_fade * vec3(0.5, 0.4, 1.0);
    bg += g2 * 0.005 * grid_fade * vec3(0.4, 0.6, 1.0);

    float moon_d = length(cuv - vec2(0.5, 0.5)) - 0.22;
    float moon_mask = smoothstep(0.002, -0.002, moon_d);
    float n_surface = noise(cuv * 18.0 + t * 0.012) * 0.5
                    + noise(cuv * 42.0 - t * 0.007) * 0.3
                    + noise(cuv * 90.0 + t * 0.02) * 0.2;
    vec3 moon_lit = vec3(0.92, 0.90, 0.82) * (0.85 + n_surface * 0.35);
    vec3 moon_umbra = vec3(0.28, 0.10, 0.32) * (0.6 + n_surface * 0.5);
    float ecl = eclipse(cuv, t);
    vec3 moon_col = mix(moon_lit, moon_umbra, ecl);
    float rim = smoothstep(0.004, 0.0, abs(moon_d + 0.006)) * (1.0 - ecl * 0.7);
    moon_col += rim * vec3(0.6, 0.55, 0.9) * 0.4;

    float glow_r = length(cuv - vec2(0.5, 0.5)) - 0.24;
    float corona = exp(-max(glow_r, 0.0) * 10.0) * (1.0 - ecl * 0.5) * 0.55;
    float blood_corona = exp(-max(glow_r, 0.0) * 7.0) * ecl * 0.6;

    vec3 col = bg;
    col += moon_mask * moon_col;
    col += corona * vec3(0.7, 0.65, 0.9);
    col += blood_corona * vec3(0.8, 0.2, 0.15);

    float archive_t = smoothstep(20.0, 22.0, t);
    for (int i = 0; i < 6; i++) {
        float fi = float(i);
        float y = 0.1 + fi * 0.135;
        float x_start = 0.1 + noise(vec2(fi, 0.0)) * 0.1;
        float x_end = x_start + 0.3 + noise(vec2(fi, 1.0)) * 0.15;
        float line_t = smoothstep(x_start, x_end, uv.x) * archive_t;
        float line_d = abs(uv.y - y);
        float line_w = 0.0008 + noise(vec2(uv.x * 20.0, fi)) * 0.0006;
        float line_v = smoothstep(line_w, 0.0, line_d) * line_t;
        float flicker = 0.7 + 0.3 * sin(t * 8.0 + fi * 1.7);
        col += line_v * vec3(0.3, 0.9, 0.7) * flicker * 0.5;
    }

    float vignette = 1.0 - smoothstep(0.35, 0.9, length(cuv - 0.5) * 1.3);
    col *= vignette;

    float fade_in = smoothstep(0.0, 2.5, t);
    float final_fade = smoothstep(28.5, 30.0, t);
    col *= fade_in * (1.0 - final_fade);

    col = pow(max(col, 0.0), vec3(0.88));
    fragColor = vec4(col, 1.0);
}
