# DJ Music Man - Manual Installation Steps (Without Docker)

These steps cover only the parts that differ when installing DJ Music Man without Docker.

## Requirements

* Python 3.11 or higher
* FFmpeg installed and available in your system's PATH
* [Deno](https://deno.com/) installed and available in your system's PATH (used by `yt-dlp` to solve YouTube's JavaScript challenges)

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

* Make sure FFmpeg and Deno are correctly installed and accessible via PATH.
* The `.env` file should still be configured as in the main installation guide.