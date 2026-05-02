import flet

# AINDA NÃO FUNCIONAL
async def go_back(page):
    if e.view is not None:
        print("View pop:", e.view)
        page.views.pop()
        top_view = page.views[-1]
        await page.push_route(top_view.route)