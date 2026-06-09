"""Seed a running instance with a realistic demo dataset.

Live scraping of LeetCode is gated behind Cloudflare (datacenter IPs are
challenged), so production ingestion requires a residential proxy via
``OXYLABS_CREDENTIALS`` (see ``scraping/submissions/run.py``). This script lets
you populate an instance without scraping: it ingests a contest, two questions
and a realistic mix of submissions through the **real** API, then runs the
**real** ``copydetect`` detection pipeline over them so genuine plagiarism
groups show up in the UI.

Usage:
    API_BASE_URL=http://localhost:8080 python seed_demo.py
"""

import os
import sys

from api_client import Client
from api_client.api.contest_controller import add_contest
from api_client.api.question_controller import add_question
from api_client.api.submission_controller import add_submissions
from api_client.models.contest import Contest
from api_client.models.question_dto import QuestionDTO
from api_client.models.submission_dto import SubmissionDTO

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8080")
CONTEST_SLUG = os.getenv("CONTEST_SLUG", "weekly-contest-506")
CONTEST_ID = int(os.getenv("CONTEST_ID", "1106"))

client = Client(base_url=API_BASE_URL)

# Two real-style contest questions (Q3 + Q4, where cheating concentrates).
Q1_ID = 3618
Q2_ID = 3619
QUESTIONS = [
    QuestionDTO(
        id=Q1_ID,
        number=3618,
        number_in_contest=3,
        name="split-array-by-prime-indices",
        description=(
            "You are given an integer array nums. Split nums into two arrays A "
            "and B such that: A contains all elements at prime indices, B "
            "contains all the remaining elements. Return the absolute "
            "difference between the sums of the two arrays."
        ),
        contest_slug=CONTEST_SLUG,
    ),
    QuestionDTO(
        id=Q2_ID,
        number=3619,
        number_in_contest=4,
        name="count-islands-with-total-value-divisible-by-k",
        description=(
            "You are given an m x n grid and an integer k. An island is a group "
            "of cells with value > 0 connected 4-directionally. The total value "
            "of an island is the sum of its cells. Return the number of islands "
            "whose total value is divisible by k."
        ),
        contest_slug=CONTEST_SLUG,
    ),
]

# --- Q1: a "copied" cluster (near-identical) + honest, distinct solutions. ---

Q1_COPIED_BASE = '''class Solution:
    def splitArray(self, nums):
        def is_prime(x):
            if x < 2:
                return False
            i = 2
            while i * i <= x:
                if x % i == 0:
                    return False
                i += 1
            return True
        a = 0
        b = 0
        for idx, val in enumerate(nums):
            if is_prime(idx):
                a += val
            else:
                b += val
        return abs(a - b)
'''

# Honest, genuinely different approaches (sieve / one-liner / functional).
Q1_HONEST = [
    '''class Solution:
    def splitArray(self, nums):
        n = len(nums)
        sieve = [True] * max(n, 2)
        sieve[0] = sieve[1] = False
        for p in range(2, int(n ** 0.5) + 1):
            if sieve[p]:
                for m in range(p * p, n, p):
                    sieve[m] = False
        prime_sum = sum(nums[i] for i in range(n) if sieve[i])
        return abs(prime_sum - (sum(nums) - prime_sum))
''',
    '''class Solution:
    def splitArray(self, nums):
        from sympy import isprime
        total = sum(nums)
        primes = sum(v for i, v in enumerate(nums) if isprime(i))
        return abs(primes - (total - primes))
''',
    '''class Solution:
    def splitArray(self, nums):
        def prime(k):
            return k > 1 and all(k % d for d in range(2, int(k ** 0.5) + 1))
        return abs(sum((1 if prime(i) else -1) * v for i, v in enumerate(nums)))
''',
    '''class Solution:
    def splitArray(self, nums):
        primes = []
        for i in range(len(nums)):
            ok = i >= 2
            for d in range(2, i):
                if i % d == 0:
                    ok = False
                    break
            primes.append(ok)
        s = sum(v for v, p in zip(nums, primes) if p)
        return abs(2 * s - sum(nums))
''',
]


def vary(code: str, who: str) -> str:
    """Trivial edits a plagiarist makes: rename vars, add blanks/comments."""
    renamed = (
        code.replace("is_prime", "check_prime")
        .replace("idx", "pos")
        .replace("val", "value")
        .replace("a +=", "first +=")
        .replace("b +=", "second +=")
        .replace("a = 0", "first = 0")
        .replace("b = 0", "second = 0")
        .replace("abs(a - b)", "abs(first - second)")
    )
    return f"# solution by {who}\n\n{renamed}\n# end\n"


Q2_COPIED_BASE = '''class Solution:
    def countIslands(self, grid, k):
        m, n = len(grid), len(grid[0])
        seen = [[False] * n for _ in range(m)]
        ans = 0
        for i in range(m):
            for j in range(n):
                if grid[i][j] > 0 and not seen[i][j]:
                    stack = [(i, j)]
                    seen[i][j] = True
                    total = 0
                    while stack:
                        x, y = stack.pop()
                        total += grid[x][y]
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < m and 0 <= ny < n and grid[nx][ny] > 0 and not seen[nx][ny]:
                                seen[nx][ny] = True
                                stack.append((nx, ny))
                    if total % k == 0:
                        ans += 1
        return ans
'''

Q2_HONEST = [
    '''class Solution:
    def countIslands(self, grid, k):
        m, n = len(grid), len(grid[0])
        parent = list(range(m * n))
        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        def union(a, b):
            parent[find(a)] = find(b)
        for i in range(m):
            for j in range(n):
                if grid[i][j] > 0:
                    if i + 1 < m and grid[i + 1][j] > 0:
                        union(i * n + j, (i + 1) * n + j)
                    if j + 1 < n and grid[i][j + 1] > 0:
                        union(i * n + j, i * n + j + 1)
        from collections import defaultdict
        comp = defaultdict(int)
        for i in range(m):
            for j in range(n):
                if grid[i][j] > 0:
                    comp[find(i * n + j)] += grid[i][j]
        return sum(1 for v in comp.values() if v % k == 0)
''',
    '''import sys
class Solution:
    def countIslands(self, grid, k):
        sys.setrecursionlimit(10 ** 6)
        m, n = len(grid), len(grid[0])
        def dfs(i, j):
            if i < 0 or j < 0 or i >= m or j >= n or grid[i][j] <= 0:
                return 0
            v = grid[i][j]
            grid[i][j] = 0
            return v + dfs(i + 1, j) + dfs(i - 1, j) + dfs(i, j + 1) + dfs(i, j - 1)
        res = 0
        for i in range(m):
            for j in range(n):
                if grid[i][j] > 0:
                    if dfs(i, j) % k == 0:
                        res += 1
        return res
''',
    '''from collections import deque
class Solution:
    def countIslands(self, grid, k):
        m, n = len(grid), len(grid[0])
        visited = set()
        count = 0
        for r in range(m):
            for c in range(n):
                if grid[r][c] > 0 and (r, c) not in visited:
                    q = deque([(r, c)])
                    visited.add((r, c))
                    s = 0
                    while q:
                        a, b = q.popleft()
                        s += grid[a][b]
                        for na, nb in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)):
                            if 0 <= na < m and 0 <= nb < n and grid[na][nb] > 0 and (na, nb) not in visited:
                                visited.add((na, nb))
                                q.append((na, nb))
                    count += s % k == 0
        return count
''',
    '''class Solution:
    def countIslands(self, grid, k):
        m, n = len(grid), len(grid[0])
        def vary2(i, j):
            if not (0 <= i < m and 0 <= j < n) or grid[i][j] <= 0:
                return 0
            val = grid[i][j]
            grid[i][j] = -1
            for di, dj in [(1,0),(-1,0),(0,1),(0,-1)]:
                val += vary2(i+di, j+dj)
            return val
        total = 0
        for i in range(m):
            for j in range(n):
                if grid[i][j] > 0 and vary2(i, j) % k == 0:
                    total += 1
        return total
''',
]


def vary2(code: str, who: str) -> str:
    renamed = (
        code.replace("countIslands", "numIslands")
        .replace("seen", "visited")
        .replace("ans", "result")
        .replace("total", "acc")
        .replace("stack", "st")
    )
    return f"# {who}'s submission\n{renamed}\n"


def build_submissions():
    subs = []
    sid = 100000
    date = 1_725_000_000

    def add(qid, code, lang, user):
        nonlocal sid, date
        subs.append(
            SubmissionDTO(
                id=sid, code=code, language=lang, date=date,
                user_slug=user, page=1, question_id=qid,
            )
        )
        sid += 1
        date += 37

    # Q1: 6 plagiarists copying the same solution + 4 honest solvers.
    for i in range(6):
        add(Q1_ID, vary(Q1_COPIED_BASE, f"cheater_q1_{i}"), "python3", f"cheater_q1_{i}")
    for i, code in enumerate(Q1_HONEST):
        add(Q1_ID, code, "python3", f"honest_q1_{i}")

    # Q2: 5 plagiarists + 4 honest solvers.
    for i in range(5):
        add(Q2_ID, vary2(Q2_COPIED_BASE, f"cheater_q2_{i}"), "python3", f"cheater_q2_{i}")
    for i, code in enumerate(Q2_HONEST):
        add(Q2_ID, code, "python3", f"honest_q2_{i}")

    return subs


def main():
    print(f"Seeding {API_BASE_URL} (contest {CONTEST_SLUG})")
    r = add_contest.sync_detailed(client=client, contest=Contest(id=CONTEST_ID, slug=CONTEST_SLUG))
    print("add_contest:", r.status_code)
    for q in QUESTIONS:
        r = add_question.sync_detailed(client=client, body=q)
        print(f"add_question {q.name}:", r.status_code)
    subs = build_submissions()
    r = add_submissions.sync_detailed(client=client, body=subs)
    print(f"add_submissions ({len(subs)}):", r.status_code)
    if r.status_code >= 300:
        print(r.content[:500])
        sys.exit(1)

    # Run the real detection pipeline against the data we just ingested.
    os.environ["API_BASE_URL"] = API_BASE_URL
    os.environ["CONTEST_SLUG"] = CONTEST_SLUG
    import processing.copydetect.run as detector
    detector.API_CLIENT = client
    detector.handler({}, None)
    print("Detection complete.")


if __name__ == "__main__":
    main()
