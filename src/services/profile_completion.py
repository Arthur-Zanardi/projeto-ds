FOTO_PADRAO = (
    "https://images.unsplash.com/photo-1524504388940-b1c1722653e1"
    "?w=900&h=1200&fit=crop"
)

VALORES_PADRAO_INCOMPLETOS = {
    "foto_url": FOTO_PADRAO,
    "imagem": FOTO_PADRAO,
    "descricao": "Perfil em construcao.",
    "localizacao": "Localizacao nao informada",
    "cargo": "Explorando novas conexoes",
}

CAMPOS_OBRIGATORIOS = ("nome", "idade", "foto_url", "localizacao", "cargo", "descricao")


def _texto(valor) -> str:
    return str(valor or "").strip()


def campos_faltantes_perfil(perfil: dict | None) -> list[str]:
    perfil = perfil or {}
    faltantes = []

    if not _texto(perfil.get("nome")):
        faltantes.append("nome")

    if perfil.get("idade") in (None, ""):
        faltantes.append("idade")

    foto = _texto(perfil.get("foto_url") or perfil.get("imagem"))
    if not foto or foto == VALORES_PADRAO_INCOMPLETOS["foto_url"]:
        faltantes.append("foto_url")

    for campo in ("localizacao", "cargo", "descricao"):
        valor = _texto(perfil.get(campo))
        if not valor or valor == VALORES_PADRAO_INCOMPLETOS[campo]:
            faltantes.append(campo)

    return faltantes


def perfil_publico_completo(perfil: dict | None) -> bool:
    return not campos_faltantes_perfil(perfil)


def anexar_status_perfil(perfil: dict | None) -> dict:
    dados = dict(perfil or {})
    faltantes = campos_faltantes_perfil(dados)
    dados["perfil_completo"] = not faltantes
    dados["campos_faltantes"] = faltantes
    return dados
