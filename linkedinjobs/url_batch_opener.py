#!/usr/bin/env python3
"""
URL Batch Opener - Open URLs from Excel in Google Chrome
Opens URLs in new tabs with customizable batch size
"""

import sys
import os
import webbrowser
import time
from openpyxl import load_workbook

def open_urls_in_chrome(excel_file, batch_size=10, start_row=1):
    """Open URLs from Excel in Chrome in batches"""
    
    print(f"\n{'='*80}")
    print("CHROME URL BATCH OPENER")
    print(f"{'='*80}\n")
    
    try:
        # Load workbook
        print(f"📂 Reading Excel file: {excel_file}")
        wb = load_workbook(excel_file)
        ws = wb.active
        
        print(f"📄 Active sheet: {ws.title}\n")
        
        # Find "Apply URL" column
        url_column = None
        url_column_name = None
        
        print("🔍 Looking for 'Apply URL' column...")
        for col_idx, cell in enumerate(ws[1], 1):
            if cell.value and 'apply' in str(cell.value).lower() and 'url' in str(cell.value).lower():
                url_column = col_idx
                url_column_name = cell.value
                print(f"   ✅ Found: '{url_column_name}' in column {col_idx}\n")
                break
        
        if not url_column:
            print("❌ ERROR: 'Apply URL' column not found in Excel!")
            print("\nAvailable columns:")
            for col_idx, cell in enumerate(ws[1], 1):
                if cell.value:
                    print(f"   - {cell.value}")
            return False
        
        # Collect URLs
        urls = []
        for row_idx in range(2, ws.max_row + 1):
            url = ws.cell(row=row_idx, column=url_column).value
            if url and str(url).startswith('http'):
                urls.append({
                    'url': url,
                    'row': row_idx
                })
        
        print(f"✓ Found {len(urls)} valid URLs\n")
        
        if not urls:
            print("❌ No URLs found in 'Apply URL' column")
            return False
        
        # Ask for batch size if not provided
        if batch_size is None:
            print("📋 Batch size options:")
            print("   1. 5 URLs at a time")
            print("   2. 10 URLs at a time")
            print("   3. 15 URLs at a time")
            print("   4. 20 URLs at a time")
            print("   5. Custom number")
            
            choice = input("\nSelect option (1-5): ").strip()
            
            if choice == '1':
                batch_size = 5
            elif choice == '2':
                batch_size = 10
            elif choice == '3':
                batch_size = 15
            elif choice == '4':
                batch_size = 20
            elif choice == '5':
                batch_size = int(input("Enter custom batch size: ").strip())
            else:
                batch_size = 10
        
        print(f"⚙️  Batch size: {batch_size} URLs per batch\n")
        
        # Ask for starting position
        print(f"Starting from row: {start_row}")
        start_idx = max(0, start_row - 2)  # Adjust for header row
        
        total_batches = (len(urls) - start_idx + batch_size - 1) // batch_size
        
        print(f"📊 Total batches: {total_batches}\n")
        
        # Open URLs in batches
        batch_num = 1
        for i in range(start_idx, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            
            print(f"{'='*80}")
            print(f"BATCH {batch_num}/{total_batches}")
            print(f"{'='*80}\n")
            
            for idx, item in enumerate(batch, 1):
                url = item['url']
                row = item['row']
                print(f"[{idx}/{len(batch)}] Row {row}: Opening {url[:60]}...")
                
                # Open URL in Chrome
                webbrowser.open(url, new=2)  # new=2 opens in new tab
                time.sleep(0.5)  # Small delay between opens
            
            print(f"\n✅ Batch {batch_num} opened ({len(batch)} URLs)")
            
            if batch_num < total_batches:
                print(f"\n⏸️  Press ENTER to open next batch ({len(urls[i + batch_size:i + batch_size + batch_size])} URLs)...")
                input()
            
            batch_num += 1
        
        print(f"\n{'='*80}")
        print("✅ ALL URLS OPENED!")
        print(f"{'='*80}\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python url_batch_opener.py <excel_file> [batch_size] [start_row]")
        print("\nExamples:")
        print("  python url_batch_opener.py jobs.xlsx")
        print("  python url_batch_opener.py jobs.xlsx 15")
        print("  python url_batch_opener.py jobs.xlsx 10 50")
        print("\nOptions:")
        print("  - Press ENTER between batches")
        print("  - Chrome will open each URL in a new tab")
        print("  - Small delay between URLs to prevent overload")
        sys.exit(1)
    
    excel_file = sys.argv[1]
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else None
    start_row = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    
    if not os.path.exists(excel_file):
        print(f"❌ Excel file not found: {excel_file}")
        sys.exit(1)
    
    success = open_urls_in_chrome(excel_file, batch_size, start_row)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()