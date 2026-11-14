from pathlib import Path
from streamlit.testing.v1 import AppTest

app = AppTest.from_file(str(Path(__file__).with_name('app.py')), default_timeout=30).run()
assert not app.exception, app.exception
assert len(app.dataframe) == 2
app.button[0].click().run()
assert not app.exception, app.exception
assert any('Private lesson cancellation' in x.value for x in app.subheader)
app.text_input[0].set_value('zzzzzzzzzz')
app.button[0].click().run()
assert any('No matching evidence' in x.value for x in app.warning)
app.text_input[0].set_value('What is the price?')
app.button[0].click().run()
assert any('Courts & prices' in x.value for x in app.warning)
app.selectbox[1].set_value(21).run()
assert not app.exception, app.exception
assert all(int(row) == 21 for row in app.dataframe[0].value['hour'])
print('PASS: initial render, policy retrieval, unknown query, operational routing and court-time filtering')

