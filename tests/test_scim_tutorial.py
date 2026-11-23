"""
tests/test_scim_tutorial.py - Comprehensive verification for stdlib/scim.ltl
Tests RFC 7643 / RFC 7644 SCIM 2.0 User and Group canonicalisation, ListResponse,
Error envelopes, PATCH operations, Bulk documents, filter AST parsing, and filter evaluation.
"""
from pathlib import Path
from lateralus_lang.compiler import Compiler, Target

def test_scim_user_and_group_canonicalization():
    scim_src = Path("stdlib/scim.ltl").read_text(encoding="utf-8")
    driver = r"""
let u = new_user("usr-123", "alice@example.com", true)
u = with_name(u, "Alice", "Smith", "Alice Smith")
u = with_email(u, "alice@work.com", "work", true)

let g = new_group("grp-456", "DevOps", ["usr-123", "usr-789"])
"""
    c = Compiler()
    res = c.compile_source(scim_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    u = ns["u"]
    assert u["id"] == "usr-123"
    assert u["userName"] == "alice@example.com"
    assert u["active"] is True
    assert u["schemas"] == ["urn:ietf:params:scim:schemas:core:2.0:User"]
    assert u["meta"]["resourceType"] == "User"
    assert u["name"]["givenName"] == "Alice"
    assert u["name"]["familyName"] == "Smith"
    assert len(u["emails"]) == 1
    assert u["emails"][0]["value"] == "alice@work.com"
    assert u["emails"][0]["primary"] is True

    g = ns["g"]
    assert g["id"] == "grp-456"
    assert g["displayName"] == "DevOps"
    assert g["schemas"] == ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    assert len(g["members"]) == 2
    assert g["members"][0]["value"] == "usr-123"

def test_scim_list_response_and_error_envelopes():
    scim_src = Path("stdlib/scim.ltl").read_text(encoding="utf-8")
    driver = r"""
let r1 = {}
r1["id"] = "1"
let r2 = {}
r2["id"] = "2"
let lr = list_response([r1, r2], 1, 10, 50)
let err = error(409, "uniqueness", "User already exists")
"""
    c = Compiler()
    res = c.compile_source(scim_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    lr = ns["lr"]
    assert lr["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    assert lr["startIndex"] == 1
    assert lr["itemsPerPage"] == 10
    assert lr["totalResults"] == 50
    assert len(lr["Resources"]) == 2

    err = ns["err"]
    assert err["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:Error"]
    assert err["status"] == "409"
    assert err["scimType"] == "uniqueness"
    assert err["detail"] == "User already exists"

def test_scim_patch_and_bulk_documents():
    scim_src = Path("stdlib/scim.ltl").read_text(encoding="utf-8")
    driver = r"""
let op1 = patch_op("replace", "active", false)
let email_val = {}
email_val["value"] = "home@example.com"
let op2 = patch_op("add", "emails", email_val)
let op3 = patch_op("remove", "name.formatted", nil)

let patch_doc = patch_document([op1, op2, op3])
let parsed = parse_patch(patch_doc)

let b_op = bulk_operation("DELETE", "/Users/usr-123", "", nil)
let bulk_doc = bulk_request(5, [b_op])
"""
    c = Compiler()
    res = c.compile_source(scim_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    parsed = ns["parsed"]
    assert len(parsed) == 3
    assert parsed[0] == ["replace", "active", False]
    assert parsed[1] == ["add", "emails", {"value": "home@example.com"}]
    assert parsed[2] == ["remove", "name.formatted", None]

    bulk = ns["bulk_doc"]
    assert bulk["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:BulkRequest"]
    assert bulk["failOnErrors"] == 5
    assert len(bulk["Operations"]) == 1

def test_scim_filter_lexing_and_ast_parsing():
    scim_src = Path("stdlib/scim.ltl").read_text(encoding="utf-8")
    driver = r"""
let toks = lex_filter("title pr and (active eq true or department sw Eng)")
let ast = parse_filter("title pr and (active eq true or department sw Eng)")
"""
    c = Compiler()
    res = c.compile_source(scim_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    toks = ns["toks"]
    assert toks == ["title", "pr", "and", "(", "active", "eq", "true", "or", "department", "sw", "Eng", ")"]

    ast = ns["ast"]
    assert ast["kind"] == "and"
    assert ast["left"]["kind"] == "pr"
    assert ast["left"]["attr"] == "title"
    assert ast["right"]["kind"] == "or"
    assert ast["right"]["left"]["kind"] == "cmp"
    assert ast["right"]["left"]["attr"] == "active"
    assert ast["right"]["left"]["op"] == "eq"
    assert ast["right"]["left"]["value"] == "true"

def test_scim_filter_evaluation_and_case_insensitivity():
    scim_src = Path("stdlib/scim.ltl").read_text(encoding="utf-8")
    driver = r"""
let u = new_user("usr-1", "BJensen@example.com", true)
u = with_name(u, "Barbara", "Jensen", "Ms. Barbara J Jensen, III")

let f_eq = parse_filter("userName eq bjensen@example.com")
let m_eq = eval_filter(f_eq, u)

let f_co = parse_filter("name.formatted co jensen")
let m_co = eval_filter(f_co, u)

let f_sw = parse_filter("name.givenName sw Barb")
let m_sw = eval_filter(f_sw, u)

let f_ew = parse_filter("name.familyName ew nsen")
let m_ew = eval_filter(f_ew, u)

let f_pr = parse_filter("name.formatted pr and active eq true")
let m_pr = eval_filter(f_pr, u)

let f_ne = parse_filter("userName ne other@example.com")
let m_ne = eval_filter(f_ne, u)
"""
    c = Compiler()
    res = c.compile_source(scim_src + "\n" + driver, target=Target.PYTHON)
    assert res.ok, f"Compilation failed: {[e.message for e in res.errors]}"
    ns = {}
    exec(res.python_src, ns)

    assert ns["m_eq"] is True, "SCIM userName comparison must be case-insensitive"
    assert ns["m_co"] is True, "SCIM substring 'co' must match"
    assert ns["m_sw"] is True, "SCIM prefix 'sw' must match"
    assert ns["m_ew"] is True, "SCIM suffix 'ew' must match"
    assert ns["m_pr"] is True, "SCIM presence 'pr' and boolean 'active eq true' must match"
    assert ns["m_ne"] is True, "SCIM inequality 'ne' must match"
