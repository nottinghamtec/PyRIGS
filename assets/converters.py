class AssetIDConverter:  # Forces lowercase to uppercase
    regex = '[^/]+'

    def to_python(self, value):
        return str(value).upper()

    def to_url(self, value):
        return str(value).upper()
