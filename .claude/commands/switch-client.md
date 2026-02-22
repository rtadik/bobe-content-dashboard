# Switch Client

> Switch the active client for all pipeline commands.

## Variables

client_id: $ARGUMENTS (the client ID to switch to)

---

## Instructions

1. **List available clients** by reading the `clients/` directory:
   ```bash
   ls -d clients/*/config.json 2>/dev/null | sed 's|clients/||;s|/config.json||'
   ```

2. **Show current active client**:
   ```bash
   cat .active-client 2>/dev/null || echo "bobe (default)"
   ```

3. **If $ARGUMENTS is provided**, validate and switch:
   - Check that `clients/{client_id}/config.json` exists
   - Write the client ID to `.active-client`
   - Read the config and display the client's display name and website
   - Confirm: "Switched to {display_name}. All pipeline commands will now use this client."

4. **If no argument**, show:
   - Current active client
   - List of all available clients with their display names
   - Ask which client to switch to
