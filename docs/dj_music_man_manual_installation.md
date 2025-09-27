# DJ Music Man - Manual Installation Steps (Without Docker)

These steps cover only the parts that differ when installing DJ Music Man without Docker.

## Requirements

* Python 3.8 or higher
* FFmpeg installed and available in your system's PATH

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Run the Bot

From the project's root directory, run:

```bash
python main.py
```

## Notes

* Make sure FFmpeg is correctly installed and accessible via PATH.
* The `.env` file should still be configured as in the main installation guide.