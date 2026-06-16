STARTERS_POR_VETOR = {
    "extroversao": "Vi que nosso jeito de viver energia social parece conversar bem. O que te recarrega mais: sair, ficar em casa ou um pouco dos dois?",
    "abertura_experiencias": "A gente parece ter uma curiosidade parecida por novidades. Qual foi a ultima coisa nova que voce topou experimentar?",
    "romantismo_afeto": "Nosso jeito de demonstrar carinho chamou minha atencao. Que tipo de gesto simples faz voce se sentir lembrado?",
    "ritmo_vida": "Parece que nosso ritmo de vida tem uma sintonia legal. Voce prefere dias bem planejados ou deixar espaco para improviso?",
    "logica_vs_emocao": "A forma como a gente equilibra razao e emocao parece interessante. Voce costuma decidir mais pelo sentimento ou pela analise?",
    "resolucao_conflitos": "Nosso jeito de lidar com conversas dificeis parece ter pontos em comum. O que ajuda voce a resolver um conflito sem pesar o clima?",
    "competitividade_cooperacao": "A gente parece combinar no equilibrio entre parceria e desafio. Voce curte mais competir brincando ou construir algo junto?",
    "ambicao_carreira": "Nossa energia para planos de futuro parece parecida. Tem algum projeto ou objetivo que tem te animado ultimamente?",
    "conservadorismo": "Parece que a gente pode render uma conversa boa sobre valores e escolhas de vida. Que tradicao ou liberdade voce valoriza muito?",
    "espectro_politico": "A gente parece ter abertura para falar de mundo sem transformar tudo em debate pesado. Que tema atual te faz pensar bastante?",
    "gestao_financeira": "Nosso jeito de lidar com dinheiro parece render assunto. Voce e mais do tipo que planeja tudo ou deixa uma parte para viver o momento?",
    "religiosidade": "A forma como espiritualidade ou sentido de vida aparece para a gente parece interessante. O que te da sensacao de direcao?",
    "gosto_festas": "A gente parece ter uma vibe social parecida. Qual seria um rolê perfeito para voce em uma sexta a noite?",
    "animes": "Vi que animes podem ser um bom ponto de partida. Qual historia voce indicaria para alguem entender seu gosto?",
    "filmes": "Parece que filmes podem render uma conversa boa. Qual filme voce reassistiria sem pensar duas vezes?",
    "series": "A gente parece ter assunto para maratonas. Qual serie te prendeu de um jeito inesperado?",
    "livros_ficcao": "Ficcao parece um terreno legal entre a gente. Qual universo ou personagem ficou na sua cabeca por dias?",
    "videogames": "Jogos parecem ser um ponto de conexao. Qual jogo voce joga pelo desafio e qual joga so para relaxar?",
    "jogos_tabuleiro": "A gente pode se divertir falando de jogos de mesa. Voce prefere estrategia longa, blefe ou algo rapido e caotico?",
    "tecnologia": "Tecnologia apareceu como uma ponte boa. Qual ferramenta, app ou ideia recente te deixou curioso?",
    "academia": "Movimento e cuidado com o corpo podem render assunto. Qual habito faz voce sentir que o dia entrou nos trilhos?",
    "esportes": "Esportes parecem ter algum espaco na nossa sintonia. Voce gosta mais de praticar, assistir ou torcer de longe?",
    "futebol": "Futebol pode ser um bom quebra-gelo. Qual jogo, time ou memoria de torcida te marcou?",
    "dancas": "Danca apareceu como uma possibilidade divertida. Voce danca sem vergonha ou precisa de um empurraozinho?",
    "musica": "Musica parece uma ponte facil entre a gente. Qual musica descreveria sua semana ate agora?",
    "tocar_instrumentos": "Instrumentos rendem uma conversa bonita. Tem algum som que voce gostaria de aprender ou ouvir ao vivo?",
    "fotografia": "Fotografia parece um ponto forte para puxar papo. Que tipo de cena faz voce querer parar e registrar?",
    "culinaria": "Culinaria pode ser um comeco gostoso. Qual prato voce faria para impressionar alguem sem sofrer na cozinha?",
    "idiomas": "Idiomas parecem render curiosidade. Que lingua ou cultura voce gostaria de conhecer mais de perto?",
    "celebridades": "Cultura pop pode ser um jeito leve de comecar. Qual assunto famoso voce fingiu nao acompanhar, mas acompanhou?",
    "historia": "Historia pode render um papo longo. Se pudesse visitar uma epoca por um dia, qual escolheria?",
    "geografia": "Geografia e lugares parecem uma boa ponte. Qual cidade ou pais esta na sua lista de curiosidade?",
    "geopolitica": "Parece que a gente pode falar de mundo com profundidade. Que mudanca global voce acha mais interessante hoje?",
    "astronomia": "Astronomia e um comeco bonito de conversa. Qual pergunta sobre o universo ainda te deixa olhando para cima?",
}


def gerar_sugestoes_inicio(dimensoes: list[dict]):
    sugestoes = []

    for dimensao in dimensoes:
        campo = dimensao.get("campo")
        sugestoes.append({
            "campo": campo,
            "rotulo": dimensao.get("rotulo") or str(campo or "").replace("_", " ").title(),
            "texto": STARTERS_POR_VETOR.get(
                campo,
                "Achei uma sintonia interessante aqui. Como esse tema aparece no seu dia a dia?",
            ),
        })

    return sugestoes
