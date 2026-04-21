import sys

with open('eden/routing.py', 'r', encoding='utf-8') as f:
    content = f.read()

s1 = '''        route = self._route_index.get(name)
        if not route:
            raise ValueError(f"Route named '{name}' not found.")'''
r1 = '''        route = self._route_index.get(name)
        if not route:
            for k, v in self._route_index.items():
                if k.endswith(f":{name}"):
                    route = v
                    name = k
                    break
        if not route:
            raise ValueError(f"Route named '{name}' not found.")'''

s2 = '''        except Exception as e:
            # Starlette raises NoMatchFound or similar if URL interpolation fails
            raise ValueError(f"Failed to generate URL for route '{name}': {e}")'''
r2 = '''        except Exception as e:
            # Starlette raises NoMatchFound or similar if URL interpolation fails
            if "No route exists" in str(e):
                raise ValueError(f"Missing path parameters for route '{name}': {e}")
            raise ValueError(f"Failed to generate URL for route '{name}': {e}")'''

content = content.replace(s1, r1)
content = content.replace(s2, r2)
with open('eden/routing.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done")
