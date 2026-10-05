# Public synthetic bug for benchmark — no customer data
def add(a, b):
    return a - b  # intentional bug

def test_add():
    assert add(2, 3) == 5
