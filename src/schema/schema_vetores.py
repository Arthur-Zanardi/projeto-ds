from pydantic import BaseModel, Field

class VetorPsicologico(BaseModel):
    # Traços Comportamentais
    extroversao: float = Field(default=0.5, description="0.0 muito introvertido/caseiro, 1.0 muito extrovertido/comunicativo")
    abertura_experiencias: float = Field(default=0.5, description="0.0 prefere rotina rígida, 1.0 busca constantemente inovações e mudanças")
    romantismo_afeto: float = Field(default=0.5, description="0.0 prático e pouco afetuoso, 1.0 demonstrações constantes de carinho")
    ritmo_vida: float = Field(default=0.5, description="0.0 calmo/slow-living, 1.0 acelerado/multitarefas")
    
    # Dinâmica Interpessoal
    logica_vs_emocao: float = Field(default=0.5, description="0.0 toma decisões com o coração, 1.0 puramente analítico e racional")
    resolucao_conflitos: float = Field(default=0.5, description="0.0 passivo/evita brigas, 1.0 confrontador/direto")
    competitividade_cooperacao: float = Field(default=0.5, description="0.0 focado em harmonia mútua, 1.0 altamente competitivo (quer vencer argumentos ou jogos)")

class VetorValores(BaseModel):
    ambicao_carreira: float = Field(default=0.5, description="0.0 trabalha só pelo básico, 1.0 altamente focado em estudos e sucesso profissional")
    conservadorismo: float = Field(default=0.5, description="0.0 progressista/desconstruído, 1.0 apegado a tradições familiares/sociais")
    espectro_politico: float = Field(default=0.5, description="0.0 extrema-esquerda, 0.5 centro, 1.0 extrema-direita")
    gestao_financeira: float = Field(default=0.5, description="0.0 gasta impulsivamente, 1.0 poupador/focado em investimentos")
    religiosidade: float = Field(default=0.5, description="0.0 ateu/materialista, 1.0 praticante fervoroso")
    gosto_festas: float = Field(default=0.5, description="0.0 odeia aglomeração, 1.0 baladeiro assíduo")

class VetorInteresses(BaseModel):
    # Entretenimento Clássico
    animes: float = Field(default=0.5)
    filmes: float = Field(default=0.5)
    series: float = Field(default=0.5, description="0.0 não assiste, 1.0 maratona séries (ex: The Boys, etc)")
    livros_ficcao: float = Field(default=0.5, description="0.0 não lê, 1.0 leitor assíduo (ex: alta fantasia, mangás, etc)")
    
    # Jogos e Tecnologia
    videogames: float = Field(default=0.5, description="0.0 não joga, 1.0 gamer hardcore/competitivo (ex: CS2, Valorant)")
    jogos_tabuleiro: float = Field(default=0.5)
    tecnologia: float = Field(default=0.5, description="0.0 leigo, 1.0 imerso no meio (ex: programa, estuda IA, desenvolvimento)")
    
    # Corpo e Movimento
    academia: float = Field(default=0.5, description="0.0 sedentário, 1.0 focado em hipertrofia e biomecânica")
    esportes: float = Field(default=0.5)
    futebol: float = Field(default=0.5)
    dancas: float = Field(default=0.5)
    
    # Artes e Cultura
    musica: float = Field(default=0.5)
    tocar_instrumentos: float = Field(default=0.5)
    fotografia: float = Field(default=0.5)
    culinaria: float = Field(default=0.5)
    idiomas: float = Field(default=0.5)
    celebridades: float = Field(default=0.5, description="0.0 ignora cultura pop/fofoca, 1.0 acompanha ativamente")
    
    # Conhecimento Acadêmico/Mundo
    historia: float = Field(default=0.5)
    geografia: float = Field(default=0.5)
    geopolitica: float = Field(default=0.5, description="0.0 não acompanha, 1.0 debate teoria política, filosofia e economia")
    astronomia: float = Field(default=0.5)

# A Classe Mestre que junta tudo
class PerfilUsuarioVetorizado(BaseModel):
    psicologico: VetorPsicologico
    valores: VetorValores
    interesses: VetorInteresses