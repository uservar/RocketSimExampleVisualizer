from pyqtgraph.opengl.shaders import ShaderProgram, VertexShader, FragmentShader

cShader = ShaderProgram('cShader', [
    VertexShader("""
#version 330
layout(location = 0) in vec3 a_position;
uniform mat4 u_mvp;
out vec3 fragPosition;

void main() {
    fragPosition = a_position;
    gl_Position = u_mvp * vec4(a_position, 1.0);
}
    """),
    FragmentShader("""
#version 330
in vec3 fragPosition;
out vec4 outColor;

void main() {
    vec3 blue = vec3(0.25, 0.5, 1.0);
    vec3 orange = vec3(1.0, 0.25, 0.15);
    float normPos = fragPosition.y / 5120.0;
    vec3 sideColor = max(normPos, 0.0) * orange - min(normPos, 0.0) * blue;
    vec3 color = sideColor + (1.0 - abs(normPos)) * 0.2;
    outColor = vec4(color, 0.3);
}
    """)
])
