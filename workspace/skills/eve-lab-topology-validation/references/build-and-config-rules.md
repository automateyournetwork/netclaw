# Build and config rules

## Build-plan sequence
1. Verify or create the lab
2. Confirm images available
3. Check host capacity
4. Create nodes
5. Verify nodes exist
6. Map interfaces
7. Create network objects
8. Connect interfaces
9. Verify topology
10. Run UNL validator
11. Start nodes
12. Apply startup configs if in scope
13. Verify connectivity

## Configuration output rules
- Use node name as hostname
- State the target OS/image at the top of each config block
- Use a stated addressing plan
- Include only requested/selected protocols
- Use `<password>` placeholders instead of fake secrets
