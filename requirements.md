# Project overview

This project is built for chess puzzles only. The puzzles database is retrieved from lichess: https://database.lichess.org/lichess_db_puzzle.csv.zst. Below is the list of the features:

- First version is web application. Backend is Python FastAPI, Frontend is Nextjs.
- Second version will support Android and iOS, built from Flutter.
- Guest can solve random puzzle.
- Authentication features for saving user progress.

# Feedback + Change request

## 2026-03-03

- I want to save user puzzle result:
  - 1 wrong move = Fail
  - All correct moves = Success
- I want to calculate user's rating based on the result of submitted puzzle.
  - Fail: reduce rating
  - Success: increase rating
  - What is the formula for reduce/increase rating?
- Query the next puzzles based on user's rating. What is the logic for it?
- User can click on the Next Puzzle button only after solving it.
- Highlight the King when it's checked. See `images/2026-03-03_14-20.png`.
- When making correct moved, add a check mark on it. See image `images/2026-03-03_14-20.png`. Wrong move will have a red mark with x.
