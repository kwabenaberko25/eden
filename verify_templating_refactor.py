
from eden.templating import EdenDirectivesExtension, TemplateLexer
from jinja2 import Environment

def test_refactor():
    ext = EdenDirectivesExtension(Environment())
    
    cases = [
        (
            "Nested Directives",
            """@if(True) {
                @if(False) {
                    Inner
                } @else {
                    Else
                }
            }""",
            "{% if True %}\n                {% if False %}\n                    Inner\n                {% else %}\n                    Else\n                {% endif %}\n            {% endif %}"
        ),
        (
            "Conditional Chain",
            "@if(x == 1) { One } @elif(x == 2) { Two } @else { Three }",
            "{% if x == 1 %} One {% elif x == 2 %} Two {% else %} Three {% endif %}"
        ),
        (
            "Switch Case",
            """@switch(status) {
                @case('active') { Active }
                @case('pending') { Pending }
                @default { Unknown }
            }""",
            "{% with __sw = status %}{% if __sw == 'active' %} Active {% elif __sw == 'pending' %} Pending {% else %} Unknown {% endif %}{% endwith %}"
        ),
        (
            "Email Protection",
            "Contact us at support@example.com or @if(True) { follow us }",
            "Contact us at support@example.com or {% if True %} follow us {% endif %}"
        ),
        (
            "Complex Expression",
            "@if(user.role in ['admin', 'editor'] and user.is_active) { Dashboard }",
            "{% if user.role in ['admin', 'editor'] and user.is_active %} Dashboard {% endif %}"
        ),
        (
            "Escaped symbol",
            "Price is @@99",
            "Price is @99"
        ),
        (
            "Link protection",
            '<a href="https://example.com" target="_blank">External</a>',
            '<a href="https://example.com" target="_blank" rel="noopener noreferrer">External</a>'
        )
    ]

    for name, source, expected in cases:
        print(f"Testing {name}...")
        try:
            tokens = TemplateLexer(source).tokenize()
            # print(f"   Tokens: {[ (t.type, t.value) for t in tokens if t.type != t.type.EOF ]}")
            result = ext.preprocess(source, None)
            if result.strip() == expected.strip():
                print(f"✅ {name} passed")
            else:
                print(f"❌ {name} failed")
                # print(f"   Expected: {repr(expected)}")
                print(f"   Got:      {repr(result)}")
        except Exception as e:
            print(f"💥 {name} errored: {e}")

if __name__ == "__main__":
    test_refactor()
