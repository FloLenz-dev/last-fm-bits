from pathlib import Path

from nicegui import ui
from rank_artists import calculate_scores

PROJECT_ROOT = Path(__file__).parent.parent

ui.label('Last.fm Artist Ranking').classes('text-h4')

file_input = ui.input(
    label='Artist File',
    value=str(PROJECT_ROOT / 'artists.txt'),
)

depth_input = ui.number(
    label='Depth',
    value=3,
    min=1,
)

breadth_input = ui.number(
    label='Breadth',
    value=10,
    min=1,
)

status = ui.label('Ready')

results_area = ui.textarea(
    label='Results',
).classes('w-full')


def run_analysis():
    status.set_text('Running...')

    results = calculate_scores(
        filepath=file_input.value,
        depth=int(depth_input.value),
        breadth=int(breadth_input.value),
    )

    results_area.value = "\n".join(
        f"{artist}: {score:.2f}"
        for artist, score in results.items()
    )

    status.set_text(
        f'Finished. Found {len(results)} matching artists.'
    )


ui.button(
    'Start Analysis',
    on_click=run_analysis,
)

ui.run(reload=False)