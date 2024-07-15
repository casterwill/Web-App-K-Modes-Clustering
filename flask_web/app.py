import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_caching import Cache
from werkzeug.security import check_password_hash, generate_password_hash
import os
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
import logging

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE':'simple'})
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.secret_key = 'supersecretkey'  # Diperlukan untuk menggunakan flash messages

ALLOWED_EXTENSIONS = {'xlsx'}

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# dummy acount
users = {
    "user1": generate_password_hash("password123"),
    "user2": generate_password_hash("mypassword")
}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def home():
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if 'username' not in request.form or 'password' not in request.form:
            flash('Form is incomplete', 'danger')
            return redirect(url_for('login'))

        username = request.form['username']
        password = request.form['password']

        if username in users and check_password_hash(users[username], password):
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        return redirect(url_for('process_file', filename=file.filename))
        # task = process_file.apply_async(args=[file.filename])
        # return redirect(url_for('task_status', task_id=task.id))
    # else:
    flash('Allowed file type is .xlsx')
    return redirect(url_for('home'))
    # return redirect(request.url)

def update_notebook_with_file_path(notebook_path, file_path):
    path_replaced = False

    # Mengubah notebook untuk menggunakan file yang diunggah
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)

    # Ganti path file dalam notebook dengan path file yang diunggah
    for cell in nb.cells:
        if cell.cell_type == 'code' and 'file_path =' in cell.source:
            cell.source = f'file_path = "{file_path}"\n' + cell.source.split('\n', 1)[1]
            path_replaced = True
            break

    if not path_replaced:
        # Jika variabel file_path tidak ditemukan, tambahkan pada sel pertama
        first_code_cell = next(cell for cell in nb.cells if cell.cell_type == 'code')
        first_code_cell.source = f'file_path = "{file_path}"\n' + first_code_cell.source

    with open(notebook_path, 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)

    logging.info("Notebook updated with file path.")

def execute_notebook(notebook_path):
    ep = ExecutePreprocessor(timeout=600, kernel_name='python3')
    with open(notebook_path, 'r', encoding='utf-8') as f:
        nb = nbformat.read(f, as_version=4)
        ep.preprocess(nb, {'metadata': {'path': './'}})
    with open(notebook_path, 'w', encoding='utf-8') as f:
        nbformat.write(nb, f)

@app.route('/process/<filename>')
@cache.cached(timeout=60) #caching 60 detik
def process_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    notebook_path = 'notebooks/k_modes_training.ipynb'

    logging.info(f"Processing file: {file_path}")

    # output_notebook_path = os.path.join('notebooks', 'k_modes_training.ipynb')

    try:
        update_notebook_with_file_path(notebook_path, file_path)
        execute_notebook(notebook_path)
        logging.info("Notebook executed successfully.")
    except Exception as e:
        logging.error(f"Error executing the notebook: {e}")
        flash('Error processing the file.')
        return redirect(url_for('home'))

    result_files = {
        # CONTOH PLOT
        'plot_example': 'static/plot_example.html',

        # TABEL PREVIEW DATA & HASIL CLUSTERING
        'output_preview_path': 'static/data_preview.html',
        'output_cluster0_path': 'static/cluster0_result.html',
        'output_cluster1_path': 'static/cluster1_result.html',

        # PLOT PRESENTASE NILAI BARIS UNIK
        'percent_IT_clust0': 'static/percent_IT_clust0.html',
        'percent_MMB_clust0': 'static/percent_MMB_clust0.html',
        'percent_IT_clust1': 'static/percent_IT_clust1.html',
        'percent_MMB_clust1': 'static/percent_IT_clust1.html',

        # 'percentage_jurusan_cluster1': 'static/cluster0_alasan_jurusan.html',
        'percentage_pens_cluster1': 'static/cluster0_alasan_pens.html',
        # 'percentage_jurusan_cluster2': 'static/cluster1_alasan_jurusan.html',
        'percentage_pens_cluster2': 'static/cluster1_alasan_pens.html',

        # TABEL EXCEL
        'raw_data_table': 'static/raw_data_table.xlsx',
        # 'baris_cluster0': 'static/baris_cluster1.xlsx',
        # 'baris_cluster1': 'static/baris_cluster2.xlsx',

        'table_cluster0': 'static/cluster0_table.xlsx',
        'table_cluster1': 'static/cluster1_table.xlsx',

        # 'minat_jurusan_total_cluster1': 'static/minat_jurusan_cluster1.xlsx',
        'minat_pens_total_cluster1': 'static/minat_pens_cluster1.xlsx',
        # 'minat_jurusan_total_cluster2': 'static/minat_jurusan_cluster2.xlsx',
        'minat_pens_total_cluster2': 'static/minat_pens_cluster2.xlsx'
    }

    if not all(os.path.exists(path) for path in result_files.values()):
        flash('Clustering process failed.')
        return redirect(url_for('home'))

    # cluster_count1 = pd.read_excel(result_files['baris_cluster0'])
    # cluster_count2 = pd.read_excel(result_files['baris_cluster1'])

    # minat_jurusan_cluster1 = pd.read_excel(result_files['minat_jurusan_total_cluster1'])
    minat_pens_cluster1 = pd.read_excel(result_files['minat_pens_total_cluster1'])
    # minat_jurusan_cluster2 = pd.read_excel(result_files['minat_jurusan_total_cluster2'])
    minat_pens_cluster2 = pd.read_excel(result_files['minat_pens_total_cluster2'])

    table_cluster1 = pd.read_excel(result_files['table_cluster0'])
    table_cluster2 = pd.read_excel(result_files['table_cluster1'])

    raw_data = pd.read_excel(result_files['raw_data_table'])

    # table_jurusan_cluster1 = minat_jurusan_cluster1.to_dict(orient='records')
    # column_jurusan_cluster1 = minat_jurusan_cluster1.columns.tolist()

    table_pens_cluster1 = minat_pens_cluster1.to_dict(orient='records')
    column_pens_cluster1 = minat_pens_cluster1.columns.tolist()

    # table_jurusan_cluster2 = minat_jurusan_cluster2.to_dict(orient='records')
    # column_jurusan_cluster2 = minat_jurusan_cluster2.columns.tolist()

    table_pens_cluster2 = minat_pens_cluster2.to_dict(orient='records')
    column_pens_cluster2 = minat_pens_cluster2.columns.tolist()

    cluter1_table = table_cluster1.to_dict(orient='records')
    column_cluster1 = table_cluster1.columns.tolist()

    cluter2_table = table_cluster2.to_dict(orient='records')
    column_cluster2 = table_cluster2.columns.tolist()

    # table_data_cluster1 = cluster_count1.to_dict(orient='records')
    # columns_cluster1 = cluster_count1.columns.tolist()
    #
    # table_data_cluster2 = cluster_count2.to_dict(orient='records')
    # columns_cluster2 = cluster_count2.columns.tolist()

    table_data_raw = raw_data.to_dict(orient='records')
    columns_raw = raw_data.columns.tolist()

    # Define the result variable
    result = {
        'status': 'Success',  # Set status or any other necessary data
        'message': 'Clustering process completed successfully.'  # Add a message if needed
    }

    return render_template(
        'result.html',
        plot_example_url=url_for('static', filename='plot_example.html'),
        preview_url=url_for('static', filename='data_preview.html'),
        cluster0_url=url_for('static', filename='cluster0_result.html'),
        cluster1_url=url_for('static', filename='cluster1_result.html'),
        # percent_jurusan_clust1=url_for('static', filename='cluster0_alasan_jurusan.html'),
        percent_it_clust1=url_for('static', filename='percent_IT_clust0.html'),
        percent_mmb_clust1=url_for('static', filename='percent_MMB_clust0.html'),
        percent_pens_clust1=url_for('static', filename='cluster0_alasan_pens.html'),
        # percent_jurusan_clust2=url_for('static', filename='cluster1_alasan_jurusan.html'),
        percent_it_clust2=url_for('static', filename='percent_IT_clust1.html'),
        percent_mmb_clust2=url_for('static', filename='percent_MMB_clust1.html'),
        percent_pens_clust2=url_for('static', filename='cluster1_alasan_pens.html'),
        # table_data_cluster1=table_data_cluster1,
        # columns_cluster1=columns_cluster1,
        # table_data_cluster2=table_data_cluster2,
        # columns_cluster2=columns_cluster2,

        # table_jurusan_clust1=table_jurusan_cluster1,
        # column_jurusan1=column_jurusan_cluster1,

        table_pens_clust1=table_pens_cluster1,
        column_pens1=column_pens_cluster1,

        # table_jurusan_clust2=table_jurusan_cluster2,
        # column_jurusan2=column_jurusan_cluster2,

        table_pens_clust2=table_pens_cluster2,
        column_pens2=column_pens_cluster2,

        clust1_table=cluter1_table,
        column_clust1=column_cluster1,
        clust2_table=cluter2_table,
        column_clust2=column_cluster2,

        table_data_raw=table_data_raw,
        columns_raw=columns_raw,
        result=result
    )

if __name__ == '__main__':
    # app.run()
    from waitress import serve
    serve(app, host='127.0.0.1', port=8000)