import asyncio
import json
import tempfile
import uuid
from pathlib import Path

from nicegui import ui

from rank_artists import ArtistScore, calculate_scores, get_artist_tags

MEDALS = {1: '🥇', 2: '🥈', 3: '🥉'}

TAG_COLORS = [
    'red-4', 'red-6', 'pink-4', 'pink-6', 'purple-4', 'purple-6',
    'deep-purple-4', 'deep-purple-6', 'indigo-4', 'indigo-6',
    'blue-4', 'blue-6', 'light-blue-4', 'light-blue-6', 'cyan-4', 'cyan-6',
    'teal-4', 'teal-6', 'green-4', 'green-6', 'light-green-4', 'light-green-6',
    'lime-4', 'lime-6', 'yellow-7', 'amber-6', 'orange-5', 'deep-orange-5',
    'brown-5', 'blue-grey-5',
]

TABLE_COLUMNS = [
    {'name': 'rank', 'label': '#', 'field': 'rank', 'align': 'left'},
    {'name': 'artist', 'label': 'Artist', 'field': 'artist', 'sortable': True, 'align': 'left'},
    {'name': 'bar', 'label': 'Match', 'field': 'bar', 'align': 'left'},
    {'name': 'score', 'label': 'Score', 'field': 'score', 'sortable': True},
    {'name': 'tags', 'label': 'Tags', 'field': 'tags', 'align': 'left'},
    {'name': 'top_contributors', 'label': 'Top Contributors', 'field': 'top_contributors',
     'sortable': True, 'align': 'left'},
]

# Each tag gets a stable color: sum of its character codes, modulo the number of colors.
TAGS_CELL_TEMPLATE = r'''
<q-td :props="props">
    <q-chip
        v-for="tag in props.value"
        :key="tag"
        dense
        outline
        :color="COLORS[tag.split('').reduce((sum, c) => sum + c.charCodeAt(0), 0) % NUM_COLORS]"
    >
        {{ tag }}
    </q-chip>
</q-td>
'''.replace('NUM_COLORS', str(len(TAG_COLORS))).replace('COLORS', json.dumps(TAG_COLORS).replace('"', "'"))

BAR_CELL_TEMPLATE = r'''
<q-td :props="props">
    <q-linear-progress :value="props.value / 100" size="12px" rounded />
</q-td>
'''

upload_state = {'path': None}


def build_row(rank: int, artist: str, score_data: ArtistScore, max_score: float) -> dict:
    return {
        'rank': MEDALS.get(rank, rank),
        'artist': artist,
        'bar': round(score_data.total_score / max_score * 100),
        'score': round(score_data.total_score),
        'tags': get_artist_tags(artist),
        'top_contributors': ', '.join(score_data.top_contributors),
    }


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
