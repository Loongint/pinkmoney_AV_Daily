#version 330
uniform float u_time;
in vec2 v_uv;
out vec4 fragColor;

float pi = 3.14159265358979323846;

float circle(vec2 uv, float r, float w) {
    float d = length(uv);
    return smoothstep(w, 0.0, abs(d - r));
}

float spiral(vec2 uv, float t) {
    float angle = atan(uv.y, uv.x);
    float dist = length(uv);
    float s = sin(angle * 13.0 - dist * pi * 6.0 + t * 1.2);
    return s * 0.5 + 0.5;
}

vec3 hsv2rgb(vec3 c) {
    vec4 K = vec4(1.0, 2.0/3.0, 1.0/3.0, 3.0);
    vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
    return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
}

void main() {
    vec2 uv = v_uv * 2.0 - 1.0;
    uv.x *= 1920.0 / 1080.0;

    float t = u_time;
    float breath = 0.5 + 0.5 * sin(t * pi * 0.3);

    vec2 rot_uv = vec2(
        uv.x * cos(t * 0.07) - uv.y * sin(t * 0.07),
        uv.x * sin(t * 0.07) + uv.y * cos(t * 0.07)
    );

    float s = spiral(rot_uv, t);

    float rings = 0.0;
    for (int i = 1; i <= 7; i++) {
        float r = 0.18 * float(i) + 0.04 * sin(t * 0.5 + float(i) * pi * 0.31415);
        rings += circle(uv, r, 0.006 + 0.004 * breath);
    }

    float pi_pulse = abs(sin(t * pi * 0.1)) * 0.6 + 0.2;

    float hue = fract(s * 0.3 + t * 0.04 + length(uv) * 0.15);
    float sat = 0.7 + 0.3 * breath;
    float val = 0.1 + s * 0.5 * pi_pulse + rings * 0.8;

    vec3 col = hsv2rgb(vec3(hue, sat, clamp(val, 0.0, 1.0)));

    vec2 center_uv = uv;
    float core_glow = exp(-length(center_uv) * (3.0 - breath * 1.5));
    col += vec3(0.6, 0.3, 0.9) * core_glow * pi_pulse;

    float vignette = 1.0 - smoothstep(0.7, 1.6, length(uv));
    col *= vignette;

    fragColor = vec4(col, 1.0);
}
