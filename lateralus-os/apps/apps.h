// ===========================================================================
// LateralusOS — Application C Stubs
// ===========================================================================
// C implementations for the Lateralus-native apps (ltlc, chat, editor, pkg).
// These stubs are compiled into the kernel and provide the VGA/framebuffer
// rendering + keyboard I/O that the pure-Lateralus modules describe.
// ===========================================================================

#ifndef APPS_H
#define APPS_H

#include "../gui/types.h"

// -- ltlc: Built-in Lateralus Compiler -----------------------------------

// Token kinds (matches apps/ltlc.ltl TokenKind enum)
enum LtlcTokenKind {
    LTLC_INT_LIT, LTLC_FLOAT_LIT, LTLC_STRING_LIT, LTLC_BOOL_LIT,
    LTLC_IDENT,
    LTLC_KW_FN, LTLC_KW_LET, LTLC_KW_MUT, LTLC_KW_IF, LTLC_KW_ELSE,
    LTLC_KW_WHILE, LTLC_KW_FOR, LTLC_KW_IN, LTLC_KW_RETURN,
    LTLC_KW_STRUCT, LTLC_KW_ENUM, LTLC_KW_MATCH, LTLC_KW_IMPORT,
    LTLC_KW_PUB, LTLC_KW_TRAIT, LTLC_KW_IMPL, LTLC_KW_ASYNC,
    LTLC_KW_AWAIT, LTLC_KW_CONST, LTLC_KW_TYPE,
    LTLC_KW_TRUE, LTLC_KW_FALSE,
    LTLC_PLUS, LTLC_MINUS, LTLC_STAR, LTLC_SLASH, LTLC_PERCENT,
    LTLC_EQ, LTLC_EQEQ, LTLC_BANGEQ, LTLC_LT, LTLC_GT,
    LTLC_LTEQ, LTLC_GTEQ, LTLC_AND, LTLC_OR, LTLC_BANG,
    LTLC_PIPE, LTLC_PIPEGT, LTLC_ARROW, LTLC_FATARROW, LTLC_DOT,
    LTLC_LPAREN, LTLC_RPAREN, LTLC_LBRACE, LTLC_RBRACE,
    LTLC_LBRACKET, LTLC_RBRACKET,
    LTLC_COMMA, LTLC_COLON, LTLC_SEMI, LTLC_NEWLINE, LTLC_EOF,
    LTLC_ERROR,
};

typedef struct {
    enum LtlcTokenKind kind;
    char value[128];
    int  line;
    int  col;
} LtlcToken;

#define LTLC_MAX_TOKENS 4096

typedef struct {
    int  ok;
    int  token_count;
    int  fn_count;
    int  struct_count;
    int  let_count;
    int  import_count;
    int  line_count;
    int  error_count;
    char errors[8][128];
} LtlcCompileResult;

// Public API
void cmd_ltlc(const char *args);
void cmd_ltlc_repl(void);
LtlcCompileResult ltlc_compile(const char *source, int len);

// -- chat: IRC-style Chat Client -----------------------------------------

#define CHAT_MAX_MESSAGES   200
#define CHAT_MAX_USERS       32
#define CHAT_MAX_CHANNELS     8
#define CHAT_MAX_MSG_LEN    256
#define CHAT_MAX_NICK_LEN    32

enum ChatMsgKind {
    CHAT_MSG_CHAT, CHAT_MSG_SYSTEM, CHAT_MSG_JOIN, CHAT_MSG_PART,
    CHAT_MSG_PRIVMSG, CHAT_MSG_ACTION, CHAT_MSG_ERROR, CHAT_MSG_MOTD,
};

typedef struct {
    enum ChatMsgKind kind;
    char sender[CHAT_MAX_NICK_LEN];
    char text[CHAT_MAX_MSG_LEN];
    uint32_t timestamp;
    uint32_t color;
} ChatMessage;

typedef struct {
    char     name[32];
    char     topic[128];
    char     users[CHAT_MAX_USERS][CHAT_MAX_NICK_LEN];
    int      user_count;
    ChatMessage messages[CHAT_MAX_MESSAGES];
    int      msg_count;
    int      unread;
} ChatChannel;

typedef struct {
    char         nick[CHAT_MAX_NICK_LEN];
    ChatChannel  channels[CHAT_MAX_CHANNELS];
    int          channel_count;
    int          active_ch;
    int          running;
    int          loopback;          // 1 = local-only mode
    char         input_buf[512];
    int          input_len;
    int          scroll_offset;
} ChatState;

// Public API
void cmd_chat(const char *args);

// -- editor: Text Editor -------------------------------------------------

#define EDIT_MAX_LINES      2048
#define EDIT_MAX_LINE_LEN    256
#define EDIT_VISIBLE_ROWS     22
#define EDIT_VISIBLE_COLS     78

enum EditorMode {
    EDIT_MODE_NORMAL, EDIT_MODE_INSERT, EDIT_MODE_COMMAND, EDIT_MODE_SEARCH,
};

typedef struct {
    char filename[128];
    char lines[EDIT_MAX_LINES][EDIT_MAX_LINE_LEN];
    int  line_count;
    int  cursor_x;
    int  cursor_y;
    int  scroll_y;
    enum EditorMode mode;
    int  modified;
    char clipboard[EDIT_MAX_LINE_LEN];
    char search_term[64];
    char status_msg[128];
    int  running;
} EditorState;

// Public API
void cmd_edit(const char *args);

// -- pkg: Package Manager ------------------------------------------------

void cmd_pkg(const char *args);

#endif // APPS_H
