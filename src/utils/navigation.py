import logging

logger = logging.getLogger(__name__)


# AINDA NÃO FUNCIONAL
async def go_back(page, e=None):
    if e is not None and e.view is not None:
        logger.debug("View pop: %s", e.view)
        page.views.pop()
        top_view = page.views[-1]
        await page.push_route(top_view.route)
