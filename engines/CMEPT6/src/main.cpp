// CMEPT6 Engine 1.1 — independent research-oriented UCI chess engine.
// SPDX-License-Identifier: MIT
// Written independently using public chess rules and classical search techniques.
#include <algorithm>
#include <cassert>
#include <array>
#include <atomic>
#include <chrono>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <stdexcept>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <vector>
#if defined(_MSC_VER)
#include <intrin.h>
#endif

namespace sfera {
using Clock = std::chrono::steady_clock;
constexpr int P = 1, N = 2, B = 3, R = 4, Q = 5, K = 6;
constexpr int WK = 1, WQ = 2, BK = 4, BQ = 8;
constexpr int INF = 32000, MATE = 30000, MAX_PLY = 100;
constexpr const char* STARTPOS = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";
constexpr std::array<int, 8> KNIGHTS = {14, 18, 31, 33, -14, -18, -31, -33};
constexpr std::array<int, 8> KINGS = {1, -1, 16, -16, 15, 17, -15, -17};
constexpr std::array<int, 4> ROOKS = {1, -1, 16, -16};
constexpr std::array<int, 4> BISHOPS = {15, 17, -15, -17};
constexpr std::array<int, 7> VALUE = {0, 100, 320, 335, 510, 970, 0};
inline bool valid(int sq) { return (sq & 0x88) == 0; }
inline int color_index(int side) { return side == 1 ? 0 : 1; }
inline int file_of(int sq) { return sq & 7; }
inline int rank_of(int sq) { return sq >> 4; }
inline int piece_index(int p) { return p > 0 ? p - 1 : 6 - p - 1; }
inline int to64(int sq) { return (sq >> 4) * 8 + (sq & 7); }
inline int to88(int sq) { return (sq / 8) * 16 + (sq % 8); }
inline uint64_t sqbit(int sq) { return uint64_t{1} << to64(sq); }
// Hybrid bitboard foundation: material and attack masks are maintained incrementally,
// while legal sliding moves still use the proven 0x88 representation.
std::array<uint64_t, 64> knight_attack_mask{}, king_attack_mask{};
std::array<std::array<uint64_t, 64>, 2> pawn_attacker_mask{};
std::array<std::array<uint64_t, 64>, 8> slider_rays{};
// A1 is bit 0, H8 is bit 63. This works on C++17, including MSVC x64.
inline int least_bit(uint64_t bits) {
    assert(bits);
#if defined(_MSC_VER) && defined(_M_X64)
    unsigned long index;
    _BitScanForward64(&index, bits);
    return int(index);
#elif defined(__GNUC__) || defined(__clang__)
    return __builtin_ctzll(bits);
#else
    int i = 0;
    while (!(bits & 1)) { bits >>= 1; ++i; }
    return i;
#endif
}
inline int greatest_bit(uint64_t bits) {
    assert(bits);
#if defined(_MSC_VER) && defined(_M_X64)
    unsigned long index;
    _BitScanReverse64(&index, bits);
    return int(index);
#elif defined(__GNUC__) || defined(__clang__)
    return 63 - __builtin_clzll(bits);
#else
    int i = 0;
    while (bits >>= 1) ++i;
    return i;
#endif
}
inline int extract_lsb(uint64_t& bits) {
    int i = least_bit(bits);
    bits &= bits - 1;
    return i;
}
// Ray direction: E, W, N, S, NE, SW, NW, SE.
constexpr std::array<int, 8> RAY_DF{1, -1, 0, 0, 1, -1, -1, 1};
constexpr std::array<int, 8> RAY_DR{0, 0, 1, -1, 1, -1, 1, -1};
uint64_t sliding_attacks(int i, uint64_t occupied, int first, int last) {
    uint64_t attacks = 0;
    for (int d = first; d < last; ++d) {
        uint64_t ray = slider_rays[d][i];
        uint64_t blockers = ray & occupied;
        if (blockers) {
            bool increasing = (RAY_DR[d] * 8 + RAY_DF[d]) > 0;
            int nearest = increasing ? least_bit(blockers) : greatest_bit(blockers);
            ray ^= slider_rays[d][nearest]; // Keep first blocker, exclude behind it.
        }
        attacks |= ray;
    }
    return attacks;
}

void init_attack_masks() {
    for (int sq = 0; sq < 128; ++sq) {
        if (!valid(sq)) continue;
        const int i = to64(sq);
        for (int d = 0; d < 8; ++d) {
            for (int f = file_of(sq) + RAY_DF[d], r = rank_of(sq) + RAY_DR[d];
                 f >= 0 && f < 8 && r >= 0 && r < 8; f += RAY_DF[d], r += RAY_DR[d])
                slider_rays[d][i] |= uint64_t{1} << (r * 8 + f);
        }
        for (int d : KNIGHTS) if (valid(sq + d)) knight_attack_mask[i] |= sqbit(sq + d);
        for (int d : KINGS) if (valid(sq + d)) king_attack_mask[i] |= sqbit(sq + d);
        for (int side : {1, -1}) {
            for (int df : {-1, 1}) {
                const int attacker = sq - 16 * side + df;
                if (valid(attacker)) pawn_attacker_mask[color_index(side)][i] |= sqbit(attacker);
            }
        }
    }
}

struct Move {
    int from, to, promotion;
    bool operator==(const Move& other) const {
        return from == other.from && to == other.to && promotion == other.promotion;
    }
};
// Fixed-capacity move list avoids heap allocation on every search node.
// FIDE chess has at most 218 legal moves in any position.
struct MoveList {
    std::array<Move, 256> data;
    std::size_t n = 0;
    void clear() { n = 0; }
    void reserve(std::size_t) {}
    void push_back(Move m) {
        if (n >= data.size()) throw std::runtime_error("MoveList capacity exceeded");
        data[n++] = m;
    }
    Move* begin() { return data.data(); }
    Move* end() { return data.data() + n; }
    const Move* begin() const { return data.data(); }
    const Move* end() const { return data.data() + n; }
    bool empty() const { return n == 0; }
    std::size_t size() const { return n; }
    Move& operator[](std::size_t index) { return data[index]; }
    const Move& operator[](std::size_t index) const { return data[index]; }
};
struct Board {
    std::array<int8_t, 128> cell{};
    std::array<uint64_t, 12> pieces{};  // piece bitboards, white indices 0..5, black 6..11
    std::array<uint64_t, 2> occupancy{}; // white and black occupancy
    int side = 1, castling = 0, ep = -1, halfmove = 0, fullmove = 1;
    int king[2] = {-1, -1};
    uint64_t key = 0;
};
// Direct incremental updates: both 0x88 mailbox and 64-bit occupancy stay in sync.
void add_piece(Board& b, int sq, int piece) {
    assert(valid(sq) && piece && b.cell[sq] == 0);
    b.cell[sq] = static_cast<int8_t>(piece);
    b.pieces[piece_index(piece)] |= sqbit(sq);
    b.occupancy[color_index(piece > 0 ? 1 : -1)] |= sqbit(sq);
}
int remove_piece(Board& b, int sq) {
    assert(valid(sq));
    int piece = b.cell[sq];
    if (piece) {
        b.cell[sq] = 0;
        b.pieces[piece_index(piece)] &= ~sqbit(sq);
        b.occupancy[color_index(piece > 0 ? 1 : -1)] &= ~sqbit(sq);
    }
    return piece;
}
struct Undo {
    int captured = 0, captured_square = -1, moved = 0;
    int castling = 0, ep = -1, halfmove = 0, fullmove = 1;
    int king[2] = {-1, -1};
    uint64_t key = 0;
};

uint64_t rand_state = 0x9e3779b97f4a7c15ULL;
uint64_t rng() {
    uint64_t z = (rand_state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}
std::array<std::array<uint64_t, 128>, 12> zpieces{};
std::array<uint64_t, 16> zcastling{};
std::array<uint64_t, 8> zep{};
uint64_t zside = 0;
void init_zobrist() {
    for (auto& arr : zpieces) for (auto& x : arr) x = rng();
    for (auto& x : zcastling) x = rng();
    for (auto& x : zep) x = rng();
    zside = rng();
}
uint64_t hash_board(const Board& b) {
    uint64_t h = zcastling[b.castling];
    if (b.ep != -1) h ^= zep[file_of(b.ep)];
    if (b.side == -1) h ^= zside;
    for (int sq = 0; sq < 128; ++sq) if (valid(sq) && b.cell[sq])
        h ^= zpieces[piece_index(b.cell[sq])][sq];
    return h;
}
int parse_square(const std::string& s) {
    if (s.size() != 2 || s[0] < 'a' || s[0] > 'h' || s[1] < '1' || s[1] > '8') return -1;
    return (s[1] - '1') * 16 + (s[0] - 'a');
}
std::string square_name(int sq) {
    if (!valid(sq)) return "??";
    return std::string{char('a' + file_of(sq)), char('1' + rank_of(sq))};
}
std::string move_name(Move m) {
    if (m.from == -1) return "0000";
    std::string s = square_name(m.from) + square_name(m.to);
    if (m.promotion) {
        const char* names = " pnbrqk";
        s += names[m.promotion];
    }
    return s;
}
int char_piece(char c) {
    int side = std::isupper(static_cast<unsigned char>(c)) ? 1 : -1;
    switch (std::tolower(static_cast<unsigned char>(c))) {
        case 'p': return side * P; case 'n': return side * N;
        case 'b': return side * B; case 'r': return side * R;
        case 'q': return side * Q; case 'k': return side * K;
        default: return 0;
    }
}
bool set_fen(Board& b, const std::string& fen) {
    Board candidate;
    std::istringstream ss(fen);
    std::string placement, side, castles, ep;
    if (!(ss >> placement >> side >> castles >> ep)) return false;
    int row = 7, col = 0;
    for (char c : placement) {
        if (c == '/') { if (col != 8 || row == 0) return false; --row; col = 0; continue; }
        if (c >= '1' && c <= '8') { col += c - '0'; if (col > 8) return false; continue; }
        int p = char_piece(c);
        if (!p || col >= 8 || row < 0) return false;
        int sq = row * 16 + col++;
        add_piece(candidate, sq, p);
        if (std::abs(p) == K) candidate.king[color_index(p > 0 ? 1 : -1)] = sq;
    }
    if (row != 0 || col != 8 || candidate.king[0] < 0 || candidate.king[1] < 0) return false;
    if (side != "w" && side != "b") return false;
    candidate.side = side == "w" ? 1 : -1;
    if (castles != "-") for (char c : castles) {
        switch(c) { case 'K': candidate.castling |= WK; break;
            case 'Q': candidate.castling |= WQ; break;
            case 'k': candidate.castling |= BK; break;
            case 'q': candidate.castling |= BQ; break;
            default: return false; }
    }
    candidate.ep = ep == "-" ? -1 : parse_square(ep);
    if (candidate.ep == -1 && ep != "-") return false;
    ss >> candidate.halfmove >> candidate.fullmove;
    if (candidate.halfmove < 0 || candidate.fullmove < 1) return false;
    candidate.key = hash_board(candidate);
    b = candidate;
    return true;
}

bool attacked(const Board& b, int square, int by) {
    const int i = to64(square);
    const int offset = by == 1 ? 0 : 6;
    if (pawn_attacker_mask[color_index(by)][i] & b.pieces[offset + P - 1]) return true;
    if (knight_attack_mask[i] & b.pieces[offset + N - 1]) return true;
    if (king_attack_mask[i] & b.pieces[offset + K - 1]) return true;
    const uint64_t occ = b.occupancy[0] | b.occupancy[1];
    if (sliding_attacks(i, occ, 4, 8) & (b.pieces[offset + B - 1] | b.pieces[offset + Q - 1])) return true;
    if (sliding_attacks(i, occ, 0, 4) & (b.pieces[offset + R - 1] | b.pieces[offset + Q - 1])) return true;
    return false;
}
bool in_check(const Board& b, int side) {
    int ksq = b.king[color_index(side)];
    return ksq < 0 || attacked(b, ksq, -side);
}
void push_promotions(MoveList& out, int from, int to, bool promotion) {
    if (promotion) for (int p : {Q, R, B, N}) out.push_back({from, to, p});
    else out.push_back({from, to, 0});
}
void generate_pseudo(const Board& b, MoveList& out, bool tactical_only = false) {
    out.clear(); out.reserve(128);
    const int side = b.side;
    for (int sq = 0; sq < 128; ++sq) {
        if (!valid(sq) || b.cell[sq] * side <= 0) continue;
        int type = std::abs(b.cell[sq]);
        if (type == P) {
            int forward = sq + side * 16;
            bool promotion = rank_of(forward) == (side == 1 ? 7 : 0);
            if (valid(forward) && b.cell[forward] == 0) {
                if (!tactical_only || promotion) push_promotions(out, sq, forward, promotion);
                int double_sq = sq + side * 32;
                if (!tactical_only && rank_of(sq) == (side == 1 ? 1 : 6) && !b.cell[double_sq])
                    out.push_back({sq, double_sq, 0});
            }
            for (int df : {-1, 1}) {
                int dst = sq + side * 16 + df;
                if (!valid(dst)) continue;
                if ((b.cell[dst] * side < 0 && std::abs(b.cell[dst]) != K) || dst == b.ep)
                    push_promotions(out, sq, dst, rank_of(dst) == (side == 1 ? 7 : 0));
            }
        } else if (type == N || type == K) {
            const int* offsets = type == N ? KNIGHTS.data() : KINGS.data();
            for (int i = 0; i < 8; ++i) {
                int dst = sq + offsets[i];
                if (!valid(dst) || b.cell[dst] * side > 0 || std::abs(b.cell[dst]) == K) continue;
                if (!tactical_only || b.cell[dst]) out.push_back({sq, dst, 0});
            }
            if (type == K && !tactical_only && !in_check(b, side)) {
                if (side == 1 && sq == 4) {
                    if ((b.castling & WK) && b.cell[7] == R && !b.cell[5] && !b.cell[6] &&
                        !attacked(b, 5, -side) && !attacked(b, 6, -side)) out.push_back({4, 6, 0});
                    if ((b.castling & WQ) && b.cell[0] == R && !b.cell[1] && !b.cell[2] && !b.cell[3] &&
                        !attacked(b, 3, -side) && !attacked(b, 2, -side)) out.push_back({4, 2, 0});
                } else if (side == -1 && sq == 116) {
                    if ((b.castling & BK) && b.cell[119] == -R && !b.cell[117] && !b.cell[118] &&
                        !attacked(b, 117, -side) && !attacked(b, 118, -side)) out.push_back({116, 118, 0});
                    if ((b.castling & BQ) && b.cell[112] == -R && !b.cell[113] && !b.cell[114] && !b.cell[115] &&
                        !attacked(b, 115, -side) && !attacked(b, 114, -side)) out.push_back({116, 114, 0});
                }
            }
        } else {
            const uint64_t occupied = b.occupancy[0] | b.occupancy[1];
            uint64_t destinations = 0;
            if (type == B || type == Q)
                destinations |= sliding_attacks(to64(sq), occupied, 4, 8);
            if (type == R || type == Q)
                destinations |= sliding_attacks(to64(sq), occupied, 0, 4);
            destinations &= ~b.occupancy[color_index(side)];
            // Never capture a king. Legal-move validation is still performed below.
            destinations &= ~(b.pieces[(side == 1 ? 6 : 0) + K - 1]);
            if (tactical_only) destinations &= b.occupancy[color_index(-side)];
            while (destinations) out.push_back({sq, to88(extract_lsb(destinations)), 0});
        }
    }
}
void make_move(Board& b, Move m, Undo& u) {
    u = {0, m.to, b.cell[m.from], b.castling, b.ep, b.halfmove, b.fullmove,
         {b.king[0], b.king[1]}, b.key};
    const int side = b.side, type = std::abs(u.moved);
    auto remove = [&](int sq) {
        int piece = b.cell[sq];
        if (piece) { b.key ^= zpieces[piece_index(piece)][sq]; remove_piece(b, sq); }
    };
    auto place = [&](int sq, int p) {
        add_piece(b, sq, p);
        b.key ^= zpieces[piece_index(p)][sq];
    };
    b.key ^= zcastling[b.castling];
    if (b.ep != -1) b.key ^= zep[file_of(b.ep)];
    u.captured = b.cell[m.to];
    if (type == P && m.to == b.ep && !u.captured && file_of(m.to) != file_of(m.from)) {
        u.captured_square = m.to - side * 16;
        u.captured = b.cell[u.captured_square];
        remove(u.captured_square);
    }
    remove(m.from);
    remove(m.to);
    place(m.to, m.promotion ? side * m.promotion : u.moved);
    if (type == K) {
        b.king[color_index(side)] = m.to;
        b.castling &= side == 1 ? ~(WK | WQ) : ~(BK | BQ);
        if (std::abs(m.to - m.from) == 2) {
            int rook_from = (m.to > m.from) ? m.from + 3 : m.from - 4;
            int rook_to = (m.to > m.from) ? m.from + 1 : m.from - 1;
            remove(rook_from); place(rook_to, side * R);
        }
    }
    if (m.from == 0 || m.to == 0) b.castling &= ~WQ;
    if (m.from == 7 || m.to == 7) b.castling &= ~WK;
    if (m.from == 112 || m.to == 112) b.castling &= ~BQ;
    if (m.from == 119 || m.to == 119) b.castling &= ~BK;
    b.ep = type == P && std::abs(m.to - m.from) == 32 ? m.from + side * 16 : -1;
    b.halfmove = (type == P || u.captured) ? 0 : b.halfmove + 1;
    if (side == -1) ++b.fullmove;
    b.side = -side;
    b.key ^= zside ^ zcastling[b.castling];
    if (b.ep != -1) b.key ^= zep[file_of(b.ep)];
}
void unmake_move(Board& b, Move m, const Undo& u) {
    remove_piece(b, m.to);
    add_piece(b, m.from, u.moved);
    if (u.captured) add_piece(b, u.captured_square, u.captured);
    if (std::abs(u.moved) == K && std::abs(m.to - m.from) == 2) {
        const int rook_from = m.to > m.from ? m.from + 3 : m.from - 4;
        const int rook_to = m.to > m.from ? m.from + 1 : m.from - 1;
        remove_piece(b, rook_to);
        add_piece(b, rook_from, (u.moved > 0 ? 1 : -1) * R);
    }
    b.side = -b.side;
    b.castling = u.castling; b.ep = u.ep;
    b.halfmove = u.halfmove; b.fullmove = u.fullmove;
    b.king[0] = u.king[0]; b.king[1] = u.king[1];
    b.key = u.key;
}
bool valid_board_state(const Board& b) {
    std::array<uint64_t, 12> bb{};
    std::array<uint64_t, 2> occ{};
    int kings[2] = {0, 0};
    for (int sq = 0; sq < 128; ++sq) {
        if (!valid(sq) || !b.cell[sq]) continue;
        int p = b.cell[sq];
        bb[piece_index(p)] |= sqbit(sq);
        occ[color_index(p > 0 ? 1 : -1)] |= sqbit(sq);
        if (std::abs(p) == K) {
            if (b.king[color_index(p > 0 ? 1 : -1)] != sq) return false;
            ++kings[color_index(p > 0 ? 1 : -1)];
        }
    }
    return bb == b.pieces && occ == b.occupancy && kings[0] == 1 && kings[1] == 1
        && !(occ[0] & occ[1]) && hash_board(b) == b.key;
}
void legal_moves(Board& b, MoveList& legal, bool tactical = false) {
    MoveList pseudo; generate_pseudo(b, pseudo, tactical);
    legal.clear(); legal.reserve(pseudo.size());
    const int side = b.side;
    for (auto m : pseudo) {
        Undo u; make_move(b, m, u);
        if (!in_check(b, side)) legal.push_back(m);
        unmake_move(b, m, u);
    }
}
bool has_legal_move(Board& b) {
    MoveList pseudo; generate_pseudo(b, pseudo);
    const int side = b.side;
    for (auto m : pseudo) {
        Undo u; make_move(b, m, u);
        const bool legal = !in_check(b, side);
        unmake_move(b, m, u);
        if (legal) return true;
    }
    return false;
}
uint64_t perft(Board& b, int depth) {
#ifdef CMEPT6_CHECK_INVARIANTS
    if (!valid_board_state(b)) throw std::runtime_error("board or zobrist invariant failed");
#endif
    if (depth == 0) return 1;
    MoveList moves; legal_moves(b, moves);
    if (depth == 1) return moves.size();
    uint64_t total = 0;
    for (auto m : moves) {
        Undo u; make_move(b, m, u);
        total += perft(b, depth - 1);
        unmake_move(b, m, u);
    }
    return total;
}
int evaluate(const Board& b) {
    int score = 0, phase = 0;
    std::array<std::array<int, 8>, 2> pawns{};
    std::array<int, 2> bishops{};
    for (int sq = 0; sq < 128; ++sq) {
        if (!valid(sq) || !b.cell[sq]) continue;
        int piece = b.cell[sq], side = piece > 0 ? 1 : -1;
        int type = std::abs(piece), file = file_of(sq);
        int rank = side == 1 ? rank_of(sq) : 7 - rank_of(sq);
        int center = (3 - std::abs(3 - file)) + (3 - std::abs(3 - rank));
        int bonus = 0;
        switch (type) {
            case P: bonus = 4 * rank + 3 * center; pawns[color_index(side)][file]++; break;
            case N: bonus = 12 * center - 25; phase += 1; break;
            case B: bonus = 6 * center - 9; bishops[color_index(side)]++; phase += 1; break;
            case R: bonus = 2 * rank; phase += 2; break;
            case Q: bonus = 2 * center; phase += 4; break;
            case K: break;
        }
        score += side * (VALUE[type] + bonus);
    }
    for (int side : {1, -1}) {
        int idx = color_index(side);
        if (bishops[idx] >= 2) score += side * 30;
        for (int file = 0; file < 8; ++file) {
            if (pawns[idx][file] > 1) score -= side * (14 * (pawns[idx][file] - 1));
            if (pawns[idx][file] && (file == 0 || pawns[idx][file - 1] == 0) &&
                (file == 7 || pawns[idx][file + 1] == 0)) score -= side * (12 * pawns[idx][file]);
        }
    }
    // King centralisation is desirable in the endgame and dangerous in the opening.
    const bool endgame = phase <= 7;
    for (int side : {1, -1}) {
        int sq = b.king[color_index(side)], f = file_of(sq), r = side == 1 ? rank_of(sq) : 7-rank_of(sq);
        int central = (3 - std::abs(3-f)) + (3 - std::abs(3-r));
        score += side * (endgame ? 9*central : -7*central);
    }
    return b.side * score + 10;
}
struct Entry { uint64_t key = 0; Move move{-1,-1,0}; int16_t depth = -1; int16_t score = 0; uint8_t bound = 0; };
class Searcher {
#ifdef CMEPT6_SEARCH_TESTS
public: // Direct search regressions only; absent from production builds.
#endif
    std::vector<Entry> tt;
    std::atomic<bool>& stopping;
    Clock::time_point started;
    int time_limit = 0;
    uint64_t node_limit = 0;
    uint64_t nodes = 0;
    uint64_t null_attempts = 0, null_cutoffs = 0, lmr_attempts = 0, lmr_researches = 0;
    uint64_t aspiration_researches = 0, pv_switches = 0, unstable_iterations = 0;
    bool uncertainty_search = false;
    int uncertainty_margin = 75;
    bool timed_out = false;
    std::array<std::array<Move, 2>, MAX_PLY> killers{};
    std::array<std::array<int, 128>, 128> history_score{};
    std::vector<uint64_t> history;

    bool check_stop() {
        if (stopping.load(std::memory_order_relaxed) || (node_limit && nodes >= node_limit)) { timed_out = true; return true; }
        if (time_limit > 0 && (nodes & 1023) == 0 &&
            std::chrono::duration_cast<std::chrono::milliseconds>(Clock::now() - started).count() >= time_limit) {
            timed_out = true; return true;
        }
        return false;
    }
    Entry* probe(uint64_t key) {
        if (tt.empty()) return nullptr;
        Entry* e = &tt[key & (tt.size() - 1)];
        return e->key == key ? e : nullptr;
    }
    void put(uint64_t key, int depth, int score, uint8_t bound, Move move, int ply) {
        if (tt.empty()) return;
        Entry& e = tt[key & (tt.size() - 1)];
        if (e.key != key || e.depth <= depth || bound == 0) {
            if (score > MATE - MAX_PLY) score += ply;
            if (score < -MATE + MAX_PLY) score -= ply;
            e = {key, move, static_cast<int16_t>(depth), static_cast<int16_t>(score), bound};
        }
    }
    int tt_score(int score, int ply) {
        if (score > MATE - MAX_PLY) return score - ply;
        if (score < -MATE + MAX_PLY) return score + ply;
        return score;
    }
    int rank_move(const Board& b, Move m, Move best, int ply) {
        if (!valid(m.from) || !valid(m.to)) return -1;
        if (m == best) return 2'000'000;
        int victim = b.cell[m.to];
        if (!victim && std::abs(b.cell[m.from]) == P && m.to == b.ep) victim = -b.side * P;
        if (victim) return 1'000'000 + VALUE[std::abs(victim)] * 20 - VALUE[std::abs(b.cell[m.from])];
        if (m.promotion) return 900'000 + VALUE[m.promotion];
        if (ply < MAX_PLY && m == killers[ply][0]) return 800'000;
        if (ply < MAX_PLY && m == killers[ply][1]) return 799'000;
        return history_score[m.from][m.to];
    }
    bool repetition(const Board& b) const {
        if (history.size() < 3) return false;
        int count = 0, checked = 0;
        for (int i = static_cast<int>(history.size()) - 1; i >= 0 && checked <= b.halfmove; --i, ++checked)
            if (history[i] == b.key && ++count >= 3) return true;
        return false;
    }
    int qsearch(Board& b, int alpha, int beta, int ply, int remaining) {
        if (check_stop()) return 0;
        ++nodes;
        if (b.halfmove >= 100 || repetition(b)) {
            // Checkmate takes precedence over a claimable draw.
            if (in_check(b, b.side)) {
                MoveList replies; legal_moves(b, replies);
                if (replies.empty()) return -MATE + ply;
            }
            return 0;
        }
        if (ply >= MAX_PLY - 1) return evaluate(b);
        bool checked = in_check(b, b.side);
        // Stalemate is a terminal draw, even at a quiet horizon or in a
        // stand-pat cutoff window. A tactical-only move list cannot detect it.
        if (!checked && !has_legal_move(b)) return 0;
        int stand = evaluate(b);
        if (!checked) {
            if (stand >= beta) return stand;
            if (stand > alpha) alpha = stand;
        }
        // Never use static evaluation as the terminal score while in check.
        // Checked nodes must still search evasions (up to MAX_PLY safety cap).
        if (remaining <= 0 && !checked) return alpha;
        // Pseudo-legal moves are checked after make_move, so each considered move
        // is made once instead of once in legal_moves and again in the search.
        MoveList moves;
        generate_pseudo(b, moves, !checked);
        std::sort(moves.begin(), moves.end(), [&](Move x, Move y) {
            return rank_move(b, x, {}, ply) > rank_move(b, y, {}, ply);
        });
        int legal_count = 0;
        const int mover = b.side;
        for (auto m : moves) {
            Undo u; make_move(b, m, u);
            if (in_check(b, mover)) { unmake_move(b, m, u); continue; }
            ++legal_count;
            history.push_back(b.key);
            int score = -qsearch(b, -beta, -alpha, ply + 1, remaining - 1);
            history.pop_back(); unmake_move(b, m, u);
            if (timed_out) return 0;
            if (score >= beta) return score;
            if (score > alpha) alpha = score;
        }
        if (checked && !legal_count) return -MATE + ply;
        return alpha;
    }
    bool has_non_pawn_material(const Board& b, int side) const {
        const int offset = color_index(side) * 6;
        return (b.pieces[offset+N-1] | b.pieces[offset+B-1] |
                b.pieces[offset+R-1] | b.pieces[offset+Q-1]) != 0;
    }
    int search(Board& b, int depth, int alpha, int beta, int ply, bool null_allowed = true) {
        if (check_stop()) return 0;
        ++nodes;
        if (b.halfmove >= 100 || repetition(b)) {
            // Checkmate takes precedence over a claimable draw.
            if (in_check(b, b.side)) {
                MoveList replies; legal_moves(b, replies);
                if (replies.empty()) return -MATE + ply;
            }
            return 0;
        }
        if (ply >= MAX_PLY - 1) return evaluate(b);
        bool checked = in_check(b, b.side);
        if (depth <= 0) return qsearch(b, alpha, beta, ply, 10);
        if (checked) ++depth; // Check extension.
        int original_alpha = alpha;
        Entry* existing = probe(b.key);
        Move tt_best = existing ? existing->move : Move{-1,-1,0};
        if (existing && existing->depth >= depth && ply > 0) {
            int s = tt_score(existing->score, ply);
            if (existing->bound == 0 || (existing->bound == 1 && s >= beta) ||
                (existing->bound == 2 && s <= alpha)) return s;
        }
        // Null-move pruning: skip a turn to establish that even a weaker position
        // is beyond beta. Disabled in check, endgames without non-pawn material,
        // near mate bounds, and on the child of another null move.
        if (null_allowed && ply > 0 && depth >= 3 && !checked
            && std::abs(beta) < MATE - MAX_PLY && has_non_pawn_material(b, b.side)
            && evaluate(b) >= beta) {
            ++null_attempts;
            int old_ep = b.ep, old_halfmove = b.halfmove, old_fullmove = b.fullmove;
            uint64_t old_key = b.key;
            if (b.ep != -1) b.key ^= zep[file_of(b.ep)];
            b.ep = -1;
            if (b.side == -1) ++b.fullmove;
            b.side = -b.side;
            b.key ^= zside;
            ++b.halfmove;
            // Use a sentinel rather than an artificial game-history position.
            history.push_back(0);
            int r = depth >= 7 ? 3 : 2;
            int null_score = -search(b, depth - r - 1, -beta, -beta + 1, ply + 1, false);
            history.pop_back();
            b.side = -b.side; b.ep = old_ep;
            b.halfmove = old_halfmove; b.fullmove = old_fullmove; b.key = old_key;
            if (timed_out) return 0;
            if (null_score >= beta) { ++null_cutoffs; return null_score; }
        }
        MoveList moves; generate_pseudo(b, moves);
        std::sort(moves.begin(), moves.end(), [&](Move x, Move y) {
            return rank_move(b, x, tt_best, ply) > rank_move(b, y, tt_best, ply);
        });
        int best_score = -INF;
        Move best{-1,-1,0};
        int move_index = 0;
        const int mover = b.side;
        for (auto m : moves) {
            bool quiet = !b.cell[m.to] && !(std::abs(b.cell[m.from]) == P && m.to == b.ep) && !m.promotion;
            Undo u; make_move(b, m, u);
            if (in_check(b, mover)) { unmake_move(b, m, u); continue; }
            history.push_back(b.key);
            bool gives_check = in_check(b, b.side);
            int score;
            if (move_index == 0) {
                score = -search(b, depth - 1, -beta, -alpha, ply + 1);
            } else {
                // PVS: use a cheap zero-window search before a full re-search.
                int reduction = 0;
                bool killer = m == killers[ply][0] || m == killers[ply][1];
                if (depth >= 3 && move_index >= 4 && quiet && !checked && !gives_check && !killer) {
                    reduction = (depth >= 7 && move_index >= 9) ? 2 : 1;
                    ++lmr_attempts;
                }
                score = -search(b, depth - 1 - reduction, -alpha - 1, -alpha, ply + 1);
                if (score > alpha && reduction > 0) {
                    ++lmr_researches;
                    score = -search(b, depth - 1, -alpha - 1, -alpha, ply + 1);
                }
                if (score > alpha && score < beta)
                    score = -search(b, depth - 1, -beta, -alpha, ply + 1);
            }
            history.pop_back(); unmake_move(b, m, u);
            ++move_index;
            if (timed_out) return 0;
            if (score > best_score) { best_score = score; best = m; }
            if (score > alpha) alpha = score;
            if (alpha >= beta) {
                if (quiet && ply < MAX_PLY) {
                    if (!(killers[ply][0] == m)) { killers[ply][1] = killers[ply][0]; killers[ply][0] = m; }
                    history_score[m.from][m.to] = std::min(100'000, history_score[m.from][m.to] + depth * depth);
                }
                break;
            }
        }
        if (move_index == 0) return checked ? -MATE + ply : 0;
        uint8_t bound = best_score >= beta ? 1 : best_score <= original_alpha ? 2 : 0;
        put(b.key, depth, best_score, bound, best, ply);
        return best_score;
    }
    std::string pv(Board board, int depth) {
        std::string result;
        std::vector<uint64_t> visited;
        for (int i = 0; i < depth && i < MAX_PLY; ++i) {
            if (std::find(visited.begin(), visited.end(), board.key) != visited.end()) break;
            visited.push_back(board.key);
            Entry* e = probe(board.key);
            if (!e || e->move.from == -1) break;
            MoveList moves; legal_moves(board, moves);
            if (std::find(moves.begin(), moves.end(), e->move) == moves.end()) break;
            if (!result.empty()) result += " ";
            result += move_name(e->move);
            Undo u; make_move(board, e->move, u);
        }
        return result;
    }
public:
    explicit Searcher(std::atomic<bool>& flag): stopping(flag) { resize_hash(32); }
    void resize_hash(int mb) {
        mb = std::max(1, std::min(1024, mb));
        const std::size_t available = (std::size_t(mb) * 1024 * 1024) / sizeof(Entry);
        std::size_t entries = 1;
        while (entries <= available / 2) entries *= 2;
        tt.assign(entries, Entry{});
    }
    void clear_hash() { std::fill(tt.begin(), tt.end(), Entry{}); }
    void set_uncertainty(bool on) { uncertainty_search = on; }
    void set_uncertainty_margin(int cp) { uncertainty_margin = std::clamp(cp, 10, 300); }
    void run(Board board, std::vector<uint64_t> previous, int max_depth, int max_ms, uint64_t max_nodes) {
        history = std::move(previous);
        if (history.empty() || history.back() != board.key) history.push_back(board.key);
        started = Clock::now(); time_limit = max_ms; node_limit = max_nodes; timed_out = false; nodes = 0;
        null_attempts = null_cutoffs = lmr_attempts = lmr_researches = 0;
        aspiration_researches = pv_switches = unstable_iterations = 0;
        Move completed{-1,-1,0};
        MoveList legal; legal_moves(board, legal);
        if (!legal.empty()) completed = legal[0];
        int previous_score = 0, previous_jump = 0;
        bool previous_switch = false;
        for (int depth = 1; depth <= std::min(MAX_PLY - 1, max_depth); ++depth) {
            if (stopping.load()) break;
            int value = 0, window_used = 0;
            bool use_aspiration = uncertainty_search && depth >= 4;
            if (!use_aspiration) value = search(board, depth, -INF, INF, 0);
            else {
                // Volatility-aware aspiration window. This is an experimental
                // search-efficiency hypothesis, NOT a claim of Elo improvement.
                int width = std::clamp(24 + 2 * previous_jump +
                    (previous_switch ? uncertainty_margin : 0), 24, 600);
                for (int attempt = 0; attempt < 6; ++attempt) {
                    int alpha = attempt == 5 ? -INF : std::max(-INF, previous_score - width);
                    int beta = attempt == 5 ? INF : std::min(INF, previous_score + width);
                    window_used = attempt == 5 ? INF : width;
                    value = search(board, depth, alpha, beta, 0);
                    if (timed_out) break;
                    if (value > alpha && value < beta) break;
                    if (attempt == 5) break;
                    ++aspiration_researches;
                    width = std::min(INF, width * 2 + 40);
                }
            }
            if (timed_out) break;
            Entry* entry = probe(board.key);
            Move current = entry && entry->move.from >= 0 ? entry->move : completed;
            bool switched = depth > 1 && !(current == completed);
            int jump = depth > 1 ? std::abs(value - previous_score) : 0;
            if (switched) ++pv_switches;
            if (depth > 1 && (jump >= uncertainty_margin || switched)) ++unstable_iterations;
            completed = current;
            previous_jump = jump;
            previous_score = value;
            previous_switch = switched;
            auto millis = std::max<int64_t>(1,
                std::chrono::duration_cast<std::chrono::milliseconds>(Clock::now() - started).count());
            std::string score = std::abs(value) > MATE - MAX_PLY
                ? "mate " + std::to_string((value > 0 ? 1 : -1) * ((MATE - std::abs(value) + 1) / 2))
                : "cp " + std::to_string(value);
            std::cout << "info depth " << depth << " score " << score
                      << " nodes " << nodes << " time " << millis << " nps " << (nodes * 1000 / millis)
                      << " pv " << pv(board, depth) << std::endl;
            if (uncertainty_search)
                std::cout << "info string CMEPT6 uncertainty depth " << depth
                          << " cp_delta " << jump << " pv_switch " << int(switched)
                          << " aspiration_width " << window_used
                          << " unstable_iterations " << unstable_iterations << std::endl;
            if (std::abs(value) >= MATE - MAX_PLY) break;
        }
        std::cout << "info string CMEPT6 stats null " << null_attempts << " cutoffs " << null_cutoffs
                  << " LMR " << lmr_attempts << " researches " << lmr_researches
                  << " aspiration_researches " << aspiration_researches
                  << " pv_switches " << pv_switches << std::endl;
        std::cout << "bestmove " << move_name(completed) << std::endl;
    }
};

class UCI {
    Board board;
    std::vector<uint64_t> game_history;
    std::atomic<bool> stop_flag{false};
    std::thread worker;
    Searcher searcher{stop_flag};
    void stop() {
        stop_flag.store(true);
        if (worker.joinable()) worker.join();
    }
    // Minimal referee interface for deterministic engine-vs-engine regression games.
    // This is a UCI extension for our test harness, not a standard UCI command.
    std::string game_status() {
        MoveList moves; legal_moves(board, moves);
        if (moves.empty()) return in_check(board, board.side) ? "checkmate" : "stalemate";
        if (board.halfmove >= 100) return "draw_50move_claimable";
        int occurrences = 0, checked = 0;
        for (int i = static_cast<int>(game_history.size()) - 1;
             i >= 0 && checked <= board.halfmove; --i, ++checked)
            if (game_history[i] == board.key) ++occurrences;
        if (occurrences >= 3) return "draw_threefold_claimable";
        int extra = 0, only_minor = 0;
        for (int sq = 0; sq < 128; ++sq) {
            if (!valid(sq) || !board.cell[sq]) continue;
            int type = std::abs(board.cell[sq]);
            if (type != K) {
                ++extra;
                if (type == N || type == B) ++only_minor;
            }
        }
        if (extra == 0 || (extra == 1 && only_minor == 1)) return "draw_dead_position";
        return "ongoing";
    }
    bool play(const std::string& notation) {
        MoveList moves; legal_moves(board, moves);
        for (auto m : moves) if (move_name(m) == notation) {
            Undo u; make_move(board, m, u);
            game_history.push_back(board.key);
            return true;
        }
        return false;
    }
    void position(const std::string& args) {
        stop(); std::istringstream in(args); std::string part; in >> part;
        Board tmp; std::string fen;
        if (part == "startpos") fen = STARTPOS;
        else if (part == "fen") {
            std::string t;
            while (in >> t) { if (t == "moves") break; if (!fen.empty()) fen += " "; fen += t; }
        } else return;
        if (!set_fen(tmp, fen)) { std::cout << "info string Invalid FEN" << std::endl; return; }
        board = tmp; game_history.clear(); game_history.push_back(board.key);
        if (part == "startpos") in >> part; // Optional 'moves' marker.
        std::string move;
        while (in >> move) {
            if (move == "moves") continue;
            if (!play(move)) { std::cout << "info string Illegal UCI move: " << move << std::endl; break; }
        }
    }
    void go(const std::string& args) {
        stop(); stop_flag.store(false);
        std::istringstream in(args); std::string token;
        int depth = 64, movetime = 0, wtime = -1, btime = -1, winc = 0, binc = 0, movestogo = 30;
        uint64_t node_limit = 0;
        bool infinite = false;
        while (in >> token) {
            if (token == "depth") in >> depth;
            else if (token == "movetime") in >> movetime;
            else if (token == "nodes") in >> node_limit;
            else if (token == "wtime") in >> wtime;
            else if (token == "btime") in >> btime;
            else if (token == "winc") in >> winc;
            else if (token == "binc") in >> binc;
            else if (token == "movestogo") in >> movestogo;
            else if (token == "infinite") infinite = true;
            else if (token == "perft") {
                int n = 1; in >> n;
                if (n < 0 || n > 7) { std::cout << "info string perft depth must be 0..7" << std::endl; return; }
                auto start = Clock::now();
                uint64_t nodes = perft(board, n);
                auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(Clock::now()-start).count();
                std::cout << "Nodes searched: " << nodes << " in " << ms << " ms" << std::endl;
                return;
            }
        }
        if (!infinite && movetime <= 0) {
            int remaining = board.side == 1 ? wtime : btime;
            int inc = board.side == 1 ? winc : binc;
            if (remaining >= 0) movetime = std::max(10, std::min(remaining / std::max(1,movestogo) + inc / 2, remaining / 3));
        }
        worker = std::thread([this, b=board, hist=game_history, depth, movetime, node_limit]() mutable {
            searcher.run(b, std::move(hist), std::max(1, depth), movetime, node_limit);
        });
    }
public:
    UCI() { set_fen(board, STARTPOS); game_history.push_back(board.key); }
    ~UCI() { stop(); }
    void loop() {
        std::string line;
        while (std::getline(std::cin, line)) {
            std::istringstream in(line); std::string cmd; in >> cmd;
            if (cmd == "uci") {
                std::cout << "id name CMEPT6 Engine 1.1" << std::endl;
                std::cout << "id author SFERA Chess Lab" << std::endl;
                std::cout << "option name Hash type spin default 32 min 1 max 1024" << std::endl;
                std::cout << "option name Clear Hash type button" << std::endl;
                std::cout << "option name UncertaintySearch type check default false" << std::endl;
                std::cout << "option name UncertaintyMargin type spin default 75 min 10 max 300" << std::endl;
                std::cout << "uciok" << std::endl;
            } else if (cmd == "isready") std::cout << "readyok" << std::endl;
            else if (cmd == "ucinewgame") { stop(); set_fen(board, STARTPOS); game_history = {board.key}; searcher.clear_hash(); }
            else if (cmd == "position") { std::string rest; std::getline(in, rest); position(rest); }
            else if (cmd == "go") { std::string rest; std::getline(in, rest); go(rest); }
            else if (cmd == "stop") stop();
            else if (cmd == "quit") { stop(); break; }
            else if (cmd == "setoption") {
                stop(); auto at = line.find("name Hash value ");
                if (at != std::string::npos) {
                    try { int mb = std::stoi(line.substr(at+16)); searcher.resize_hash(mb); }
                    catch (...) { std::cout << "info string Invalid Hash option" << std::endl; }
                } else if (line.find("name UncertaintySearch value ") != std::string::npos) {
                    auto at = line.find("name UncertaintySearch value ");
                    std::istringstream opt(line.substr(at + std::string("name UncertaintySearch value ").size()));
                    std::string v; opt >> v;
                    std::transform(v.begin(), v.end(), v.begin(), [](unsigned char c) { return char(std::tolower(c)); });
                    searcher.set_uncertainty(v == "true" || v == "1");
                } else if (line.find("name UncertaintyMargin value ") != std::string::npos) {
                    auto at = line.find("name UncertaintyMargin value ");
                    try { searcher.set_uncertainty_margin(std::stoi(line.substr(at + std::string("name UncertaintyMargin value ").size()))); }
                    catch (...) { std::cout << "info string Invalid UncertaintyMargin option" << std::endl; }
                } else if (line.find("name Clear Hash") != std::string::npos) searcher.clear_hash();
            }
            else if (cmd == "d") {
                for (int r=7;r>=0;--r) {
                    for (int f=0;f<8;++f) {
                        int p = board.cell[16*r+f];
                        char ch = p == 0 ? '.' : " PNBRQK"[std::abs(p)];
                        std::cout << (p < 0 ? char(std::tolower(ch)) : ch) << ' ';
                    }
                    std::cout << std::endl;
                }
            }
            else if (cmd == "perft") { int n; if (in >> n && n>=0 && n<=7) std::cout << "perft " << n << " " << perft(board,n) << std::endl; }
            else if (cmd == "verify") std::cout << "verify " << (valid_board_state(board) ? "ok" : "FAILED") << std::endl;
            else if (cmd == "status") std::cout << "status " << game_status() << std::endl;
        }
    }
};
} // namespace sfera
int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    sfera::init_zobrist();
    sfera::init_attack_masks();
    sfera::UCI engine;
    engine.loop();
    return 0;
}
