from .store import Store, canonical, now


def test_iban(number: int) -> str:
    bban = "99999999" + f"{number:010d}"
    check = 98 - int(bban + "131400") % 97
    return f"DE{check:02d}{bban}"


SUPPLIERS = [
    {
        "id": "nordlicht",
        "name": "Nordlicht Facilities GmbH",
        "iban": test_iban(1001),
        "contact": "Mara Vogel · saved supplier contact",
        "phone": "+49 000 000 1001 (fictional)",
        "currency": "EUR",
        "version": 1,
        "verification": "Synthetic pre-approved supplier account",
    },
    {
        "id": "linden",
        "name": "Linden IT Services",
        "iban": test_iban(1002),
        "contact": "Leon Hart · saved supplier contact",
        "phone": "+49 000 000 1002 (fictional)",
        "currency": "EUR",
        "version": 1,
        "verification": "Synthetic pre-approved supplier account",
    },
    {
        "id": "atlas",
        "name": "Atlas Logistics s.r.o.",
        "iban": test_iban(1003),
        "contact": "Eva Novak · saved supplier contact",
        "phone": "+420 000 000 103 (fictional)",
        "currency": "EUR",
        "version": 1,
        "verification": "Synthetic pre-approved supplier account",
    },
]

OBLIGATIONS = [
    {
        "id": "PO-2609-014",
        "supplier_id": "nordlicht",
        "description": "Quarterly facilities maintenance",
        "amount_minor": 124000,
        "currency": "EUR",
        "version": 1,
        "approved": True,
    },
    {
        "id": "PO-2609-028",
        "supplier_id": "linden",
        "description": "September managed IT service",
        "amount_minor": 86000,
        "currency": "EUR",
        "version": 1,
        "approved": True,
    },
    {
        "id": "PO-2609-031",
        "supplier_id": "atlas",
        "description": "Approved cross-border freight",
        "amount_minor": 213500,
        "currency": "EUR",
        "version": 1,
        "approved": True,
    },
]


def seed_workspace(store: Store, workspace: str):
    with store.transaction() as db:
        db.execute("INSERT INTO workspaces(id,created,policy) VALUES(?,?,?)", (workspace, now(), "{}"))
        for supplier in SUPPLIERS:
            db.execute(
                "INSERT INTO suppliers VALUES(?,?,?)", (workspace, supplier["id"], canonical(supplier))
            )
        for obligation in OBLIGATIONS:
            db.execute(
                "INSERT INTO obligations VALUES(?,?,?)", (workspace, obligation["id"], canonical(obligation))
            )
