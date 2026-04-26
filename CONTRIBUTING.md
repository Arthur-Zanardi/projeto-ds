# Contribuindo para o MatchAI 🤝

Bem-vindo ao time! Para manter a qualidade do código e a agilidade do SCRUM, siga estas diretrizes:

## 🌿 Estratégia de Branchs
- `main`: Código estável e pronto para demonstração.
- `developer`: Branch de integração das funcionalidades da Sprint atual para cada desenvolvedor.
- `feature/nome-da-feature`: Branch para desenvolvimento de novas tarefas.

## 🏗️ Padrões de Código
- **Async/Await:** Como usamos Flet e APIs externas, todas as chamadas de rede/IA devem ser assíncronas.
- **MVC + Services:** Não coloque lógica de IA dentro das Views. Crie um Service em `src/services/` e chame-o através de um Controller.
- **Clean Code:** Tente aderir aos padrões estabelecidos neste [doc](https://docs.google.com/document/d/1VsjZOmuIE6xwqX6GkzYR8DSCWdKbUxnnjzqULNFnSAU/edit?usp=sharing) sempre que possível.

## 🚀 Processo de Pull Request
1. Garanta que seu código está formatado e sem erros.
2. Abra o PR apontando para a branch adequado.
3. Aguarde o Code Review de pelo menos um integrante.
4. Após aprovado, realize o Merge.
