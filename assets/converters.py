class AssetIDConverter:  # Forces lowercase to uppercase
    regex = '[^/]+'

    def to_python(self, value):
        return value.upper()

    def to_url(self, value):
        return value.upper()
