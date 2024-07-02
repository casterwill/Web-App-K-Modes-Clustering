import logging
import os
import pandas as pd
from rq import get_current_job
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

logging.basicConfig(level=logging.INFO)

# @celery.task(bind=True)
def process_file(filename):
    logging.info(f"Task received with filename: {filename}")
    try:
        job = get_current_job()
        job.meta['current'] = 0
        job.meta['total'] = 100
        job.meta['status'] = 'Proocessing'
        job.save_meta()

        file_path = os.path.join('uploads', filename)
        notebook_path = 'notebooks/k_modes_training.ipynb'
        path_replaced = False

        logging.info(f"Processing file: {file_path}")

        # Mengubah notebook untuk menggunakan file yang diunggah
        with open(notebook_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)

        # Ganti path file dalam notebook dengan path file yang diunggah
        for cell in nb.cells:
            if cell.cell_type == 'code' and 'file_path =' in cell.source:
                lines = cell.source.split('\n', 1)
                logging.info(f"Updating notebook cell: {lines}")
                if len(lines) == 2:
                    cell.source = f'file_path = "{file_path}"\n' + lines[1]
                # else:
                #     logging.error(f"Unexpected cell format: {cell.source}")
                #     raise ValueError("Unexpected cell format")
                path_replaced = True
                break

        if not path_replaced:
            # Jika variabel file_path tidak ditemukan, tambahkan pada sel pertama
            first_code_cell = next(cell for cell in nb.cells if cell.cell_type == 'code')
            first_code_cell.source = f'file_path = "{file_path}"\n' + first_code_cell.source
            logging.info(f"Added file path to the first code cell.")

        logging.info("Notebook updated with file path.")

        # Menjalankan notebook Jupyter dengan nbconvert
        ep = ExecutePreprocessor(timeout=600, kernel_name='python3')
        output_notebook_path = os.path.join('notebooks', 'k_modes_training.ipynb')

        with open(output_notebook_path, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)

        with open(output_notebook_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
            ep.preprocess(nb, {'metadata': {'path': './'}})

        with open(output_notebook_path, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)


        job.meta['current'] = 100
        job.meta['status'] = 'Completed'
        job.meta['result_url'] = 'templates/result.html'
        job.save_meta()

        logging.info("Notebook executed successfully.")

        # CONTOH PLOT
        plot_example = 'static/plot_example.html'

        # TABEL PREVIEW DATA & HASIL CLUSTERING
        output_preview_path = 'static/data_preview.html'
        output_cluster0_path = 'static/cluster0_result.html'
        output_cluster1_path = 'static/cluster1_result.html'

        # PLOT PRESENTASE NILAI BARIS UNIK
        percentage_jurusan_cluster1 = 'static/cluster0_alasan_jurusan.html'
        percentage_pens_cluster1 = 'static/cluster0_alasan_pens.html'
        percentage_jurusan_cluster2 = 'static/cluster1_alasan_jurusan.html'
        percentage_pens_cluster2 = 'static/cluster1_alasan_pens.html'

        # TABEL EXCEL
        raw_data_table = 'static/raw_data_table.xlsx'
        jumlah_baris_cluster0 = 'static/baris_cluster1.xlsx'
        jumlah_baris_cluster1 = 'static/baris_cluster2.xlsx'

        # Pastikan semua file hasil proses clustering ada
        required_files = [
            output_preview_path,
            output_cluster0_path,
            output_cluster1_path,
            jumlah_baris_cluster0,
            jumlah_baris_cluster1,
            plot_example,
            raw_data_table,
            percentage_jurusan_cluster1,
            percentage_pens_cluster1,
            percentage_jurusan_cluster2,
            percentage_pens_cluster2
        ]

        for file in required_files:
            if not os.path.exists(file):
                logging.error(f'Missing file: {file}')
                return {'status': 'failed', 'message': f'Missing file: {file}'}

        cluster_count1 = pd.read_excel(jumlah_baris_cluster0)
        cluster_count2 = pd.read_excel(jumlah_baris_cluster1)
        raw_data = pd.read_excel(raw_data_table)

        table_data_cluster1 = cluster_count1.to_dict(orient='records')
        columns_cluster1 = cluster_count1.columns.tolist()

        table_data_cluster2 = cluster_count2.to_dict(orient='records')
        columns_cluster2 = cluster_count2.columns.tolist()

        table_data_raw = raw_data.to_dict(orient='records')
        columns_raw = raw_data.columns.tolist()

        logging.info("Data prepared for rendering.")

        result = {
            'status': 'success',
            'message': 'File processed successfully.',
            'plot_example_url': 'static/plot_example.html',
            'preview_url': 'static/data_preview.html',
            'cluster0_url': 'static/cluster0_result.html',
            'cluster1_url': 'static/cluster1_result.html',
            'percent_jurusan_clust1': 'static/cluster0_alasan_jurusan.html',
            'percent_pens_clust1': 'static/cluster0_alasan_pens.html',
            'percent_jurusan_clust2': 'static/cluster1_alasan_jurusan.html',
            'percent_pens_clust2': 'static/cluster1_alasan_pens.html',
            'table_data_cluster1': table_data_cluster1,
            'columns_cluster1': columns_cluster1,
            'table_data_cluster2': table_data_cluster2,
            'columns_cluster2': columns_cluster2,
            'table_data_raw': table_data_raw,
            'columns_raw': columns_raw,
        }
        return result

    except Exception as e:
        logging.error(f"Error in process_file task: {e}")
        job.meta['status'] = 'failed'
        job.save_meta()
        return {'status': 'failed', 'message': str(e)}