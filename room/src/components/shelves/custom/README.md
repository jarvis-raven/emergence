# Custom Shelves

This directory is for **agent-specific custom shelves**.

## How to Add a Custom Shelf

1. Create a new JSX component file in this directory (e.g., `MyCustomShelf.jsx`)
2. Follow the pattern from `LibraryShelfView.jsx`:
   - Accept `data` prop containing shelf data
   - Return JSX for your shelf's UI
   - Use Tailwind classes for styling

3. Register your shelf in `ShelfRenderer.jsx`:

   ```javascript
   import MyCustomShelf from './custom/MyCustomShelf';

   const shelfRenderers = {
     // ... other renderers
     'my-custom-shelf': MyCustomShelf,
   };
   ```

4. Create the shelf data directory:

   ```bash
   mkdir -p ~/.openclaw/state/shelves/my-custom-shelf
   ```

5. Add your data file:

   ```bash
   echo '{"myData": "value"}' > ~/.openclaw/state/shelves/my-custom-shelf/data.json
   ```

6. Add shelf configuration:

   ```bash
   echo '{"id": "my-custom-shelf", "name": "My Shelf", "icon": "🎯", "renderer": "my-custom-shelf"}' > ~/.openclaw/state/shelves/my-custom-shelf/shelf.json
   ```

7. Rebuild the frontend:
   ```bash
   npm run build
   ```

## Git Protection

**Important:** Files in this directory are `.gitignore`d. They won't be committed to the Emergence repo.

This means:

- ✅ Your custom shelves stay on your machine
- ✅ Repo updates won't overwrite your shelves
- ✅ Aurora can have different shelves than you
- ✅ Standard Room shelves live in the parent directory (committed)

## Examples

See `LibraryShelfView.jsx` for a complete example of a custom shelf that displays:

- Currently reading books with progress bars
- To-read queue
- Reading statistics

## Tips

- Keep shelf names unique (no duplicates)
- Use descriptive icons (emoji work great)
- Data files support hot reloading (no rebuild needed for data changes)
- Component changes require `npm run build`
- Check browser console for errors if shelf doesn't appear

## Troubleshooting

**Shelf not showing?**

1. Check `~/.openclaw/state/shelves/<shelf-id>/shelf.json` exists
2. Verify `renderer` field matches your component name
3. Run `npm run build` after component changes
4. Check browser console for import errors

**Data not loading?**

1. Verify API returns data: `curl http://localhost:8800/api/shelves/<shelf-id>`
2. Check data file is valid JSON
3. Ensure ShelfRenderer imports your component correctly

## Built-in vs Custom

**Built-in shelves** (in parent directory):

- Drives, Memory, Aspirations, etc.
- Part of Emergence core
- Updated with repo
- All agents have them

**Custom shelves** (this directory):

- Library, personal projects, etc.
- Agent-specific
- Stay local
- Each agent has different ones
