// Independent mailbox reference to verify bitboard ray calculations.
// Build: c++ -std=c++17 -O2 tests/slider_fuzz.cpp -o slider-fuzz
#define main cmept6_embedded_main
#include "../src/main.cpp"
#undef main
#include <random>

using namespace sfera;
uint64_t slow_ray(const Board& b, int sq, int d0, int d1) {
    uint64_t mask = 0;
    for (int d = d0; d < d1; ++d) {
        int df = RAY_DF[d], dr = RAY_DR[d];
        for (int f = file_of(sq) + df, r = rank_of(sq) + dr;
             f >= 0 && f < 8 && r >= 0 && r < 8; f += df, r += dr) {
            int other = r * 16 + f;
            mask |= sqbit(other);
            if (b.cell[other]) break;
        }
    }
    return mask;
}
int main() {
    init_zobrist();
    init_attack_masks();
    const std::array<const char*, 6> positions = {{
        STARTPOS,
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
        "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
        "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
        "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10"
    }};
    std::mt19937_64 random(0xC0FFEE);
    uint64_t checked = 0;
    for (const char* fen : positions) {
        Board b;
        if (!set_fen(b, fen)) return 1;
        for (int ply = 0; ply < 260; ++ply) {
            if (!valid_board_state(b)) return 2;
            const uint64_t occupied = b.occupancy[0] | b.occupancy[1];
            for (int sq = 0; sq < 128; ++sq) {
                if (!valid(sq)) continue;
                for (int first : {0, 4}) {
                    uint64_t expected = slow_ray(b, sq, first, first+4);
                    uint64_t actual = sliding_attacks(to64(sq), occupied, first, first+4);
                    if (expected != actual) {
                        std::cerr << "Ray mismatch at " << square_name(sq) << " ply " << ply << '\n';
                        return 3;
                    }
                    ++checked;
                }
            }
            MoveList moves; legal_moves(b, moves);
            if (moves.empty()) break;
            Move m = moves[random() % moves.size()];
            Undo undo;
            Board original = b;
            make_move(b, m, undo);
            if (!valid_board_state(b)) return 4;
            if ((ply % 7) == 0) {
                Board advanced = b;
                unmake_move(b, m, undo);
                if (!valid_board_state(b) || b.key != original.key ||
                    b.pieces != original.pieces || b.cell != original.cell || b.occupancy != original.occupancy) return 5;
                b = advanced;
            }
        }
    }
    std::cout << "PASS bitboard slider reference checks: " << checked << '\n';
}
