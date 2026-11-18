// Direct search regression: terminal scores must not depend on stand-pat/window.
// Build baseline with -DCMEPT6_TEST_SOURCE="path/to/testable-baseline.cpp".
#define CMEPT6_SEARCH_TESTS
#define main cmept6_embedded_main
#ifndef CMEPT6_TEST_SOURCE
#define CMEPT6_TEST_SOURCE "../src/main.cpp"
#endif
#include CMEPT6_TEST_SOURCE
#undef main

using namespace sfera;

bool same_board(const Board& a, const Board& b) {
    return a.cell == b.cell && a.pieces == b.pieces && a.occupancy == b.occupancy
        && a.king[0] == b.king[0] && a.king[1] == b.king[1] && a.side == b.side && a.castling == b.castling
        && a.ep == b.ep && a.halfmove == b.halfmove
        && a.fullmove == b.fullmove && a.key == b.key;
}

int main() {
    init_zobrist(); init_attack_masks();
    std::atomic<bool> stopped{false};
    Searcher searcher(stopped);
    Board board;
    int failures = 0, checks = 0;
    auto require = [&](bool success, const char* label, int actual) {
        ++checks;
        if (!success) { ++failures; std::cerr << "FAIL " << label << ": " << actual << '\n'; }
    };
    const char* stalemates[] = {
        "7k/5K2/6Q1/8/8/8/8/8 b - - 0 1",
        "8/8/8/8/8/6q1/5k2/7K w - - 0 1",
        // Black pawn is blocked; pseudo-legal king moves all expose check.
        "7k/p4K2/P5Q1/8/8/8/8/8 b - - 0 1"
    };
    for (const char* fen : stalemates) {
        if (!set_fen(board, fen)) return 2;
        MoveList legal; legal_moves(board, legal);
        // Verify fixtures with full move generation before testing qsearch.
        if (!legal.empty() || in_check(board, board.side)) {
            std::cerr << "Bad stalemate fixture: " << fen << '\n'; return 3;
        }
        const Board before = board;
        for (int remaining : {0, 10}) {
            for (auto window : std::array<std::pair<int,int>,3>{{{-INF, INF}, {-2500,-2000}, {2000,2500}}}) {
                int score = searcher.qsearch(board, window.first, window.second, 0, remaining);
                require(score == 0, "qsearch stalemate", score);
                require(same_board(before, board) && valid_board_state(board), "board restoration", score);
            }
        }
        int score = searcher.search(board, 0, -INF, INF, 0);
        require(score == 0, "depth-zero search stalemate", score);
    }
    set_fen(board, "7k/6Q1/5K2/8/8/8/8/8 b - - 0 1");
    require(searcher.qsearch(board,-INF,INF,0,0)==-MATE, "checked horizon mate", 0);
    set_fen(board, STARTPOS);
    const Board before = board;
    const int expected = evaluate(board);
    require(searcher.qsearch(board,-INF,INF,0,0)==expected, "quiet legal horizon", expected);
    require(same_board(before,board), "quiet horizon restoration", 0);
    std::cout << checks << " checks, " << failures << " failures\n";
    return failures ? 1 : 0;
}


