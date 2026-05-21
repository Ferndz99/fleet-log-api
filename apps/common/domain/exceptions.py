class DomainError(Exception):
    """
    Excepción base para errores de dominio / aplicación.
    """

    status_code = 400
    title = "Domain Error"
    default_detail = "A domain rule was violated."
    code = "domain_error"

    def __init__(
        self, *, detail: str | None = None, errors: list[dict] | None = None, **context
    ):
        if detail is not None:
            self.detail = detail
        else:
            try:
                self.detail = self.default_detail.format(**context)
            except KeyError:
                self.detail = self.default_detail
        self.errors = errors
        super().__init__(self.detail)
