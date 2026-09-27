import asyncio
import tempfile
import uuid
from pathlib import Path

from nicegui import ui

from rank_artists import calculate_scores
from results_table import BAR_CELL_TEMPLATE, TABLE_COLUMNS, TAGS_CELL_TEMPLATE, build_row

upload_state = {'path': None}


async def handle_upload(e):
    upload_state['path'] = Path(tempfile.gettempdir()) / f'{uuid.uuid4()}.txt'
    upload_state['path'].write_bytes(await e.file.read())
    status.set_text(f'Geladen: {e.file.name}')


async def run_analysis():
    status.set_text('Running...')
    start_button.visible = False
    spinner.visible = True

    try:
        status.set_text('Running analysis...')

        if upload_state['path'] is None:
            status.set_text('Bitte zuerst eine Datei hochladen.')
            return

        results = await asyncio.to_thread(
            calculate_scores,
            filepath=str(upload_state['path']),
            depth=int(depth_input.value),
            breadth=int(breadth_input.value),
        )

        max_score = max((score.total_score for score in results.values()), default=1)

        table.rows = [
            build_row(rank, artist, score_data, max_score)
            for rank, (artist, score_data) in enumerate(results.items(), start=1)
        ]
        table.visible = True
        table.update()

        status.set_text(f'Finished. Found {len(results)} matching artists.')

    except Exception as e:
        status.set_text(f'Error: {e}')

    finally:
        start_button.visible = True
        spinner.visible = False


ui.page_title('Last.fm Artist Matcher')

with ui.column().classes('items-center w-full'):
    with ui.card().classes('w-full max-w-7xl'):
        ui.label('🎵 Last.fm Artist Matcher').classes('text-3xl font-bold')
        ui.label('Score artists based on similarity to your Last.fm listening habits.').classes('text-gray-500')

        spinner = ui.spinner(size='lg')
        spinner.visible = False

        ui.upload(label='Artist File', on_upload=handle_upload, auto_upload=True) \
            .props('accept=.txt').classes('w-full')

        with ui.row().classes('w-full'):
            depth_input = ui.number(label='Depth', value=3, min=1)
            breadth_input = ui.number(label='Breadth', value=10, min=1)

        status = ui.label('Ready').classes('text-primary')

        table = ui.table(columns=TABLE_COLUMNS, rows=[]).classes('w-full')
        table.add_slot('body-cell-tags', TAGS_CELL_TEMPLATE)
        table.add_slot('body-cell-bar', BAR_CELL_TEMPLATE)
        table.visible = False

        start_button = ui.button('Start Analysis', on_click=run_analysis).props('color=primary')

ui.run(reload=False)
