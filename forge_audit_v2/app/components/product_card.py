from eden.components import Component, register

@register("product_card")
class ProductCardComponent(Component):
    """
    ProductCard component.
    """
    template_name = "components/product_card.html"

    def get_context_data(self, **kwargs):
        # Add your component logic here
        return kwargs
