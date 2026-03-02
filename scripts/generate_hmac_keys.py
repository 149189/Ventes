"""Generate HMAC secret keys for merchants."""
import secrets


def generate(count=5):
    print("Generated HMAC Secret Keys:")
    print("-" * 70)
    for i in range(1, count + 1):
        key = secrets.token_hex(32)
        print(f"  Key {i}: {key}")
    print("-" * 70)
    print(f"\nEach key is {len(key)} characters (256-bit hex).")


if __name__ == '__main__':
    import sys
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    generate(count)
