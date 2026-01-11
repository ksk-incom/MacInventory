#!/bin/bash
# MacInventory Plugin Updater
# Runs outside Claude Code to update the marketplace and plugin

echo "Updating MacInventory..."
echo ""

# Update marketplace to get latest plugin listings
echo "Step 1: Updating marketplace..."
claude plugin marketplace update macinventory-marketplace

echo ""

# Update the plugin itself
echo "Step 2: Updating plugin..."
claude plugin update macinventory@macinventory-marketplace

echo ""
echo "Update complete!"
echo "Please restart Claude Code for the changes to take effect."
