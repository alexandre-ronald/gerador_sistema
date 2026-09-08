def resolve_active_workspace(workspace_projection, *, workspace_id=""):
    """Resolve deterministicamente o Workspace ativo dentro da projeção visível.

    A projeção recebida já deve estar filtrada por RBAC. Um Workspace solicitado
    só é aceito quando continua visível; caso contrário, o default visível é
    usado e, por último, o primeiro Workspace visível.
    """
    projection = workspace_projection if isinstance(workspace_projection, dict) else {}
    workspaces = projection.get("workspaces") if isinstance(projection.get("workspaces"), list) else []
    if not workspaces:
        return None

    requested_workspace = str(workspace_id or "").strip()
    if requested_workspace:
        selected_workspace = next(
            (workspace for workspace in workspaces if workspace.get("id") == requested_workspace),
            None,
        )
        if selected_workspace is not None:
            return selected_workspace

    default_id = str(projection.get("default_workspace") or "").strip()
    return next(
        (workspace for workspace in workspaces if workspace.get("id") == default_id),
        workspaces[0],
    )


def resolve_workspace_navigation_context(workspace_projection, *, workspace_id="", item_id=""):
    """Resolve o contexto navegacional sem criar uma segunda identidade de rota.

    ``workspace_id`` e ``item_id`` são IDs declarativos estáveis. O destino real
    continua sendo a URL canônica da experiência (CRUD, relatório, página etc.).
    A função só aceita itens presentes na projeção já filtrada por RBAC.
    """
    selected_workspace = resolve_active_workspace(
        workspace_projection,
        workspace_id=workspace_id,
    )
    if selected_workspace is None:
        return None

    requested_item = str(item_id or "").strip()
    selected_section = None
    selected_item = None
    for section in selected_workspace.get("sections") or []:
        for item in section.get("items") or []:
            if item.get("workspace_item_id") == requested_item or item.get("id") == requested_item:
                selected_section = section
                selected_item = item
                break
        if selected_item is not None:
            break

    if selected_item is None:
        home_id = str(selected_workspace.get("home") or "").strip()
        for section in selected_workspace.get("sections") or []:
            for item in section.get("items") or []:
                if item.get("workspace_item_id") == home_id or item.get("id") == home_id:
                    selected_section = section
                    selected_item = item
                    break
            if selected_item is not None:
                break

    if selected_item is None:
        return None

    resolved_item_id = selected_item.get("workspace_item_id") or selected_item.get("id")
    return {
        "workspace_id": selected_workspace.get("id"),
        "workspace_label": selected_workspace.get("label"),
        "section_id": selected_section.get("id"),
        "section_label": selected_section.get("label"),
        "item_id": resolved_item_id,
        "item_label": selected_item.get("label"),
        "url_name": selected_item.get("url_name"),
        "is_home": resolved_item_id == selected_workspace.get("home"),
        "breadcrumbs": [
            {"kind": "workspace", "id": selected_workspace.get("id"), "label": selected_workspace.get("label")},
            {"kind": "section", "id": selected_section.get("id"), "label": selected_section.get("label")},
            {"kind": "item", "id": resolved_item_id, "label": selected_item.get("label")},
        ],
    }
