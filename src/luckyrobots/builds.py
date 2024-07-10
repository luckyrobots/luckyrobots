import requests
import curses
import os

def get_files_from_folder(folder_id):
    url = f"https://www.googleapis.com/drive/v3/files"
    params = {
        "q": f"'{folder_id}' in parents",
        "key": "AIzaSyDTaRC95-CsIE5NZupKmxG5ZeKUKCP2ZhU",
        "pageSize": 1000
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        items = response.json().get('files', [])
        return [item for item in items if item['mimeType'] != 'application/vnd.google-apps.folder']
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return []

def download_file(file_id, file_name):
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    params = {
        "key": "AIzaSyDTaRC95-CsIE5NZupKmxG5ZeKUKCP2ZhU",
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        with open(file_name, 'wb') as f:
            f.write(response.content)
        print(f"File '{file_name}' downloaded successfully.")
    else:
        print(f"Error downloading file: {response.status_code} - {response.text}")

def interactive_file_selection(stdscr, files):
    curses.curs_set(0)
    current_row = 0
    selected_files = set()

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        for idx, file in enumerate(files):
            x = 5
            y = idx + 3
            if y >= height:
                break

            if idx == current_row:
                stdscr.attron(curses.A_REVERSE)
            if idx in selected_files:
                stdscr.addstr(y, x-3, "* ")
            stdscr.addstr(y, x, file['name'][:width-x-1])
            if idx == current_row:
                stdscr.attroff(curses.A_REVERSE)

        stdscr.addstr(1, 5, "Use arrow keys to navigate, Space to select, Enter to download")
        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(files) - 1:
            current_row += 1
        elif key == ord(' '):
            if current_row in selected_files:
                selected_files.remove(current_row)
            else:
                selected_files.add(current_row)
        elif key == 10:  # Enter key
            break

    return [files[i] for i in selected_files]

def main(stdscr):
    folder_id = '15iYXzqFNEg1b2E6Ft1ErwynqBMaa0oOa'
    files = get_files_from_folder(folder_id)

    if not files:
        print("No files found in the folder.")
        return

    selected_files = interactive_file_selection(stdscr, files)

    curses.endwin()

    if selected_files:
        print("Downloading selected files:")
        for file in selected_files:
            download_file(file['id'], file['name'])
    else:
        print("No files selected for download.")

if __name__ == '__main__':
    curses.wrapper(main)