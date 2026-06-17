import asyncio
from pathlib import Path
from nicegui import ui
from rank_artists import calculate_scores

PROJECT_ROOT = Path(__file__).parent.parent

ui.page_title('Last.fm Artist Matcher')

with ui.column().classes('items-center w-full'):

    with ui.card().classes('w-full max-w-4xl'):

        ui.label(
            '🎵 Last.fm Artist Matcher'
        ).classes(
            'text-3xl font-bold'
        )

        ui.label(
            'Score artists based on similarity to your Last.fm listening habits.'
        ).classes(
            'text-gray-500'
        )

        status = ui.label('Ready')

        spinner = ui.spinner(size='lg')
        spinner.visible = False

        file_input = ui.input(
            label='Artist File',
            value=str(PROJECT_ROOT / 'artists.txt'),
        ).classes(
            'w-full'
        )

        with ui.row().classes('w-full'):

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

        status = ui.label(
            'Ready'
        ).classes(
            'text-primary'
        )

        table = ui.table(
            columns=[
                {
                    'name': 'rank',
                    'label': '#',
                    'field': 'rank',
                    'align': 'left',
                },
                {
                    'name': 'artist',
                    'label': 'Artist',
                    'field': 'artist',
                    'sortable': True,
                    'align': 'left',
                },
                {
                    'name': 'score',
                    'label': 'Score',
                    'field': 'score',
                    'sortable': True,
                },
            ],
            rows=[],
        ).classes('w-full')
        table.visible = False

        async def run_analysis():

            status.set_text('Running...')
            start_button.visible = False
            spinner.visible = True

            try:
                status.set_text('Running analysis...')

                results = await asyncio.to_thread(
                    calculate_scores,
                    filepath=file_input.value,
                    depth=int(depth_input.value),
                    breadth=int(breadth_input.value),
                )

                table.rows = [
                    {
                        'rank': rank,
                        'artist': artist,
                        'score': round(score),
                    }
                    for rank,(artist, score) in enumerate(
                        results.items(),
                        start=1
                    )
                ]

                table.visible = True
                table.update()

                status.set_text(
                    f'Finished. Found {len(results)} matching artists.'
                )

            except Exception as e:

                status.set_text(
                    f'Error: {e}'
                )

            finally:
                start_button.visible = True
                spinner.visible = False


        start_button = ui.button(
            'Start Analysis',
            on_click=run_analysis,
        ).props('color=primary')

ui.run(reload=False)