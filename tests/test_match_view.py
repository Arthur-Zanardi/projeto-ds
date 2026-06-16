from src.views.match_view import montar_perfil_match


def test_montar_perfil_match_prefere_match_id_salvo_ao_id_sqlite():
    perfil = montar_perfil_match(
        {
            "id": 1,
            "match_id": "user_beatriz",
            "nome": "Beatriz Lima",
            "afinidade": "88%",
            "dados_match": {
                "id": "user_beatriz",
                "match_id": "user_beatriz",
                "idade": 19,
                "descricao": "Perfil salvo",
            },
        }
    )

    assert perfil["id"] == "user_beatriz"
    assert perfil["match_id"] == "user_beatriz"
    assert perfil["descricao"] == "Perfil salvo"
