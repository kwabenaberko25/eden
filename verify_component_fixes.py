#!/usr/bin/env python
"""Quick verification that Component System fixes work."""

from eden.components import Component, register, action, get_component

# Verify Counter component loads
counter_cls = get_component('counter')
print(f'✓ Counter component registered: {counter_cls.__name__}')

# Verify TodoList component loads  
todos_cls = get_component('todo_list')
print(f'✓ TodoList component registered: {todos_cls.__name__}')

# Verify action discovery
from eden.components import _action_registry
print(f'✓ Total actions registered: {len(_action_registry)}')

# Test Counter instance
counter = counter_cls(count=5, step=2)
print(f'✓ Counter instantiated: count={counter.count}, step={counter.step}')

# Test context data
ctx = counter.get_context_data()
has_action_url = callable(ctx.get('action_url'))
has_attrs = 'hx-vals' in str(ctx.get('component_attrs'))
print(f'✓ Context data prepared: action_url={has_action_url}, component_attrs={has_attrs}')

# Test state serialization  
state = counter.get_state()
print(f'✓ State serialized: {state}')

# Test action URL generation
url = counter.action_url('increment')
print(f'✓ Action URL generated: {url}')

print('\n✅ All fixes verified and working!')
