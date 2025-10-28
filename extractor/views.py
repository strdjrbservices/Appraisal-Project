from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from .services import extract_fields_from_pdf, FIELD_SECTIONS, SUBJECT_FIELDS
from bs4 import BeautifulSoup
from .comparison import compare_pdfs, extract_fields_from_html, compare_data_sets
import fitz  # PyMuPDF
import re

# The view to handle the initial PDF upload
async def upload_pdf(request):
    if request.method == 'POST' and request.FILES.get('pdf_file'):
        pdf_file = request.FILES['pdf_file']
        fs = FileSystemStorage()
        # Save the file to a temporary location
        filename = fs.save(pdf_file.name, pdf_file)
                
        # Create display names for the buttons
        sections_for_template = {key: key.replace('_', ' ').title() for key in FIELD_SECTIONS.keys()}

        # Instead of extracting, render the new home page with section buttons
        return render(request, 'home.html', {'filename': filename, 'sections': sections_for_template})

    return render(request, 'upload.html')

async def compare_pdfs_view(request):
    if request.method == 'POST' and request.FILES.get('pdf_file1') and request.FILES.get('pdf_file2'):
        pdf_file1 = request.FILES['pdf_file1']
        pdf_file2 = request.FILES['pdf_file2']
        fs = FileSystemStorage()

        filename1 = fs.save(pdf_file1.name, pdf_file1)
        filename2 = fs.save(pdf_file2.name, pdf_file2)

        pdf1_path = fs.path(filename1)
        pdf2_path = fs.path(filename2)

        comparison_results = await compare_pdfs(pdf1_path, pdf2_path)

        context = {
            'filename1': filename1,
            'filename2': filename2,
            'results': comparison_results,
        }
        return render(request, 'compare_results.html', context)

    return render(request, 'compare_upload.html')

def _extract_from_html_file(file_path):
    """Extracts data from the HTML file using BeautifulSoup."""
    data = {}
    fields = ['Client/Lender Name', 'Lender Address', 'FHA Case Number',
              'Transaction Type', 'AMC Reg. Number', 'Borrower (and Co-Borrower)',
              'Property Type', 'Property Address', 'Property County',
              'Appraisal Type', 'Assigned to Vendor(s)', 'UAD XML Report']
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser')

        def get_text_safe(element_id, default="N/A"):
            element = soup.find(id=element_id)
            return element.get_text(strip=True) if element else default

        data['Client/Lender Name'] = get_text_safe('ctl00_cphBody_lblLender')
        data['Lender Address'] = get_text_safe('ctl00_cphBody_lblLenderAddress')
        data['FHA Case Number'] = get_text_safe('ctl00_cphBody_lblFHACaseNumber')
        data['Transaction Type'] = get_text_safe('ctl00_cphBody_lblTransactionType')
        data['AMC Reg. Number'] = get_text_safe('ctl00_cphBody_lblAMCRegistrationNumber')
        data['Borrower (and Co-Borrower)'] = get_text_safe('ctl00_cphBody_lblBorrowerName')
        data['Property Type'] = get_text_safe('ctl00_cphBody_lblPropertyType')
        data['Property Address'] = get_text_safe('ctl00_cphBody_lblPropertyAddress')
        data['Property County'] = get_text_safe('ctl00_cphBody_lblPropertyCounty')
        data['Appraisal Type'] = get_text_safe('ctl00_cphBody_lblAppraisalType')
        data['Assigned to Vendor(s)'] = get_text_safe('ctl00_cphBody_lblAssignedTo')

        uad_xml_link = soup.find(id='ctl00_cphBody_lnkAppraisalXMLFile')
        data['UAD XML Report'] = uad_xml_link.get_text(strip=True) if uad_xml_link else "N/A"

    except FileNotFoundError:
        for field in fields:
            data[field] = "N/A (HTML File Error)"
    except Exception:
        for field in fields:
             data[field] = "N/A (HTML Processing Error)"
    return data

async def _extract_from_pdf_file(file_path):
    """Extracts data from the PDF file using the Gemini API service."""
    # Extract data from multiple sections of the PDF.
    subject_data = await extract_fields_from_pdf(file_path, 'subject')
    improvements_data = await extract_fields_from_pdf(file_path, 'improvements')
    certification_data = await extract_fields_from_pdf(file_path, 'certification')
    appraisal_id_data = await extract_fields_from_pdf(file_path, 'appraisal_id')

    # Check for errors in the primary 'subject' data extraction
    if 'error' in subject_data:
        return {key: f"N/A (API Error: {subject_data['error']})" for key in [
            'Client/Lender Name', 'Lender Address', 'FHA Case Number', 'Transaction Type',
            'AMC Reg. Number', 'Borrower (and Co-Borrower)', 'Property Type', 'Unit Number',
            'Property Address', 'Property County', 'Appraisal Type', 
            'Assigned to Vendor(s)', 'UAD XML Report'
        ]}
    
    # Map the API response fields to the keys expected by the comparison logic.
    # Helper to safely get data from potentially errored responses.
    def get_data(data_dict, key, default="N/A"):
        if 'error' in data_dict:
            return f"N/A (API Error)"
        return data_dict.get(key, default)

    def find_fha_case_number_manually(path_to_pdf):
        """Scans the top-right of PDF pages for an FHA Case Number."""
        try:
            doc = fitz.open(path_to_pdf)
            # Regex for FHA Case Number format (e.g., 123-4567890)
            fha_regex = re.compile(r'\d{3}-\d{7}')
            # Check the first 5 pages, which is where it usually is
            for page_num in range(min(5, len(doc))):
                page = doc.load_page(page_num)
                # Define a more precise top-right corner (e.g., right 30% of width, top 10% of height)
                rect = fitz.Rect(page.rect.width * 0.7, 0, page.rect.width, page.rect.height * 0.1)
                text = page.get_text("text", clip=rect)
                match = fha_regex.search(text)
                if match:
                    return match.group(0)
        except Exception:
            return None  # Return None if any error occurs
        finally:
            if 'doc' in locals() and doc:
                doc.close()

    def clean_value(value):
        if isinstance(value, str):
            return re.sub(r'[,:;]', '', value)
        return value

    def simplify_transaction_type(value):
        if not isinstance(value, str):
            return value
        if 'purchase' in value.lower():
            return 'Purchase'
        if 'refinance' in value.lower():
            return 'Refinance'
        return value
        
    # Logic to extract Unit Number for Condos
    unit_number = "N/A"
    pdf_appraisal_type = get_data(appraisal_id_data, 'This Report is one of the following types:', '')
    pdf_property_type = get_data(improvements_data, 'Type', '')
    full_address = get_data(subject_data, 'Property Address', '')

    if 'condo' in str(pdf_appraisal_type).lower() or '1073' in str(pdf_appraisal_type) or 'condo' in str(pdf_property_type).lower():
        # Regex to find common unit number patterns (e.g., Unit 104, #104, Apt 104, Condo 104)
        match = re.search(r'(?i)(?:unit|#|apt|condo)\s*(\w+)', full_address)
        if match:
            unit_number = match.group(1)

    # Get FHA case number from subject data first
    fha_case_number = get_data(subject_data, 'FHA Case Number', None)
    # If not found via API, try manual search as a fallback
    if not fha_case_number or fha_case_number == 'N/A (Not in Subject Section)':
        fha_case_number = find_fha_case_number_manually(file_path) or 'N/A'

    mapped_data = {
        'Client/Lender Name': clean_value(get_data(subject_data, 'Lender/Client')),
        'Lender Address': clean_value(get_data(subject_data, 'Address (Lender/Client)')),
        'FHA Case Number': fha_case_number,
        'Transaction Type': simplify_transaction_type(get_data(subject_data, 'Assignment Type')),
        'AMC Reg. Number': 'N/A (Not in PDF)',
        'Borrower (and Co-Borrower)': get_data(subject_data, 'Borrower'),
        'Property Type': get_data(improvements_data, 'Type'),
        'Unit Number': unit_number,
        'Property Address': (
            f"{get_data(subject_data, 'Property Address', '')} "
            f"{get_data(subject_data, 'City', '')}, {get_data(subject_data, 'State', '')} "
            f"{get_data(subject_data, 'Zip Code', '')}"
        ).strip(),
        'Property County': get_data(subject_data, 'County'),
        'Appraisal Type': pdf_appraisal_type,
        'Assigned to Vendor(s)': get_data(certification_data, 'Name'),
        'UAD XML Report': 'N/A (Not in PDF)',
    }

    return mapped_data

async def compare_html_pdf_view(request):
    if request.method == 'POST' and request.FILES.get('pdf_file') and request.FILES.get('html_file'):
        pdf_file = request.FILES['pdf_file']
        html_file = request.FILES['html_file']
        fs = FileSystemStorage()

        # Save files
        pdf_filename = fs.save(pdf_file.name, pdf_file)
        html_filename = fs.save(html_file.name, html_file)
        pdf_path = fs.path(pdf_filename)
        html_path = fs.path(html_filename)

        # Extract data using the new helper functions
        html_data = _extract_from_html_file(html_path)
        pdf_data = await _extract_from_pdf_file(pdf_path)

        # Compare the extracted data
        comparison_results = compare_data_sets(html_data, pdf_data)

        context = {
            'pdf_filename': pdf_filename,
            'html_filename': html_filename,
            'results': comparison_results,
            'html_data': html_data,
            'pdf_data': pdf_data,
        }
        return render(request, 'compare_html_pdf_results.html', context)

    return render(request, 'compare_html_pdf_upload.html')


# The new view to handle extraction for a specific section
async def extract_section(request, filename, section_name):
    fs = FileSystemStorage()
    uploaded_file_path = fs.path(filename)

    if not fs.exists(uploaded_file_path):
        return render(request, 'error.html', {'error_message': 'The requested file could not be found. Please upload it again.'})

    # Get custom prompt from POST data if it exists
    custom_prompt = request.POST.get('custom_prompt', None)

    # Handle the initial GET request for the custom analysis page
    if section_name == 'custom_analysis' and request.method == 'GET':
        sections_for_template = {key: key.replace('_', ' ').title() for key in FIELD_SECTIONS.keys()}
        context = {'data': {}, 'section_title': 'Custom Document Analysis', 'filename': filename, 'section_key': section_name, 'sections': sections_for_template}
        return render(request, 'result.html', context)

    try:
        # Call the async extraction function with the specific section name
        extracted_data = await extract_fields_from_pdf(uploaded_file_path, section_name, custom_prompt=custom_prompt)
        
        # Create display names for the sidebar sections
        sections_for_template = {key: key.replace('_', ' ').title() for key in FIELD_SECTIONS.keys()}

        # Pass the dictionary to the result template
        context = {
            'data': extracted_data,
            'section_title': section_name.replace('_', ' ').title(),
            'filename': filename,
            'section_key': section_name,
            'sections': sections_for_template,
            'custom_prompt': custom_prompt,
        }
        return render(request, 'result.html', context)
    except Exception as e:
        return render(request, 'error.html', {'error_message': str(e)})