import pytest
from pydantic import ValidationError

from src.schema.schema_vetores import PerfilUsuarioVetorizado


def test_schema_aceita_e_arredonda_valores_centesimais():
    perfil = PerfilUsuarioVetorizado(
        psicologico={"extroversao": 0.644},
        valores={"religiosidade": 0.963},
        interesses={"musica": 0.5},
    )

    assert perfil.psicologico.extroversao == 0.64
    assert perfil.valores.religiosidade == 0.96
    assert perfil.interesses.musica == 0.5


def test_schema_rejeita_valores_fora_da_escala():
    with pytest.raises(ValidationError):
        PerfilUsuarioVetorizado(
            psicologico={"extroversao": 1.2},
            valores={},
            interesses={},
        )
