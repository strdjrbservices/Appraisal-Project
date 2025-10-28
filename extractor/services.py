from google import genai
import json
from django.conf import settings
import logging # Import logging module
from google.api_core import exceptions as google_exceptions
import asyncio
import time

# SUBJECT
SUBJECT_FIELDS = [
    'Property Address', 'City', 'County', 'State', 'Zip Code', 'Borrower', 'Owner of Public Record',
    'Legal Description', "Assessor's Parcel #", 'Tax Year', 'R.E. Taxes $', 'Neighborhood Name', 'Map Reference',
    'Census Tract', 'Occupant', 'Special Assessments $', 'PUD', 'HOA $', 'HOA(per year/per month)',
    'Property Rights Appraised', 'Assignment Type', 'Lender/Client', 'Address (Lender/Client)',
    'Offered for Sale in Last 12 Months', 'Report data source(s) used, offering price(s), and date(s)',
]

# CONTRACT
CONTRACT_FIELDS = [
    'I _____ analyze the contract for sale for the subject purchase transaction.', 
    'Explain the results of the analysis of the contract for sale or why the analysis was not performed.',
    'Contract Price $', 'Date of Contract', 'Is the property seller the owner of public record?(Yes/No)', 'Data Source(s)',
    'Is there any financial assistance (loan charges, sale concessions, gift or downpay i etc.) to be paid by any party on behalf of the borrower?(Yes/No)',
    'If Yes, report the total dollar amount and describe the items to be paid.',
]

# NEIGHBORHOOD
NEIGHBORHOOD_FIELDS = [
    "Location", "Built-Up", "Growth", "Property Values", "Demand/Supply",
    "Marketing Time", "One-Unit", "2-4 Unit", "Multi-Family", "Commercial", "Other", "Present Land Use Other Description", "one unit housing price(high,low,pred)", "one unit housing age(high,low,pred)",
    "Neighborhood Boundaries", "Neighborhood Description", "Market Conditions:",
]

# SITE
SITE_FIELDS = [
    "Dimensions", "Area", "Shape", "View", "Specific Zoning Classification", "Zoning Description",
    "Zoning Compliance", "Is the highest and best use of subject property as improved (or as proposed per plans and specifications) the present use?",
    "Electricity", "Gas", "Water", "Sanitary Sewer", "Street", "Alley", "FEMA Special Flood Hazard Area",
    "FEMA Flood Zone", "FEMA Map #", "FEMA Map Date", "Are the utilities and off-site improvements typical for the market area?",
    "Are there any adverse site conditions or external factors (easements, encroachments, environmental conditions, land uses, etc.)(Yes/No)?",
    "If Yes, describe",
]

# IMPROVEMENTS
IMPROVEMENTS_FIELDS = [
    "Units", "# of Stories", "Type", "Existing/Proposed/Under Const.",
    "Design (Style)", "Year Built", "Effective Age (Yrs)", "Foundation Type",
    "Basement Area sq.ft.", "Basement Finish",
    "Evidence of", "Foundation Walls (Material/Condition)",
    "Exterior Walls (Material/Condition)", "Roof Surface (Material/Condition)",
    "Gutters & Downspouts (Material/Condition)", "Window Type (Material/Condition)",
    "Storm Sash/Insulated", "Screens", "Floors (Material/Condition)", "Walls (Material/Condition)",
    "Trim/Finish (Material/Condition)", "Bath Floor (Material/Condition)", "Bath Wainscot (Material/Condition)",
    "Attic", "Heating Type", "Fuel", "Cooling Type",
    "Fireplace(s) #", "Patio/Deck", "Pool", "Woodstove(s) #", "Fence", "Porch", "Other Amenities",
    "Car Storage", "Driveway # of Cars", "Driveway Surface", "Garage # of Cars", "Carport # of Cars",
    "Garage (Att./Det./Built-in)", "Appliances (Refrigerator,Range/Oven, Dishwasher, Disposal, Microwave, Washer/Dryer, Other (describe))",
    "Finished area above grade Rooms", "Finished area above grade Bedrooms",
    "Finished area above grade Bath(s)", "Square Feet of Gross Living Area Above Grade",
    "Additional features", "Describe the condition of the property",
    "Are there any physical deficiencies or adverse conditions that affect the livability, soundness, or structural integrity of the property?", "If Yes, describe",
    "Does the property generally conform to the neighborhood (functional utility, style, condition, use, construction, etc.)?", "If No, describe",
]

# This list defines the fields for a single property in the sales comparison grid (both subject and comparables).
# The prompt will instruct the AI to use this for the subject and for each comparable found.
SALES_COMPARISON_APPROACH_FIELDS = [
    "Address", 
    "Proximity to Subject", 
    "Sale Price", 
    "Sale Price/Gross Liv. Area",
    "Data Source(s)", 
    "Verification Source(s)",
    "Sale or Financing Concessions", "Sale or Financing Concessions Adjustment",
    "Date of Sale/Time", "Date of Sale/Time Adjustment",
    "Location", "Location Adjustment",
    "Leasehold/Fee Simple", "Leasehold/Fee Simple Adjustment",
    "Site", "Site Adjustment",
    "View", "View Adjustment",
    "Design (Style)", "Design (Style) Adjustment",
    "Quality of Construction", "Quality of Construction Adjustment",
    "Actual Age", "Actual Age Adjustment",
    "Condition", "Condition Adjustment",
    "Total Rooms", "Bedrooms", "Baths",
    "Gross Living Area", "Gross Living Area Adjustment",
    "Basement & Finished Rooms Below Grade", "Basement & Finished Rooms Below Grade Adjustment",
    "Functional Utility", "Functional Utility Adjustment",
    "Heating/Cooling", "Heating/Cooling Adjustment",
    "Energy Efficient Items", "Energy Efficient Items Adjustment",
    "Garage/Carport", "Garage/Carport Adjustment",
    "Porch/Patio/Deck", "Porch/Patio/Deck Adjustment",
    "Net Adjustment (Total)", "Adjusted Sale Price of Comparable",
]

SALES_COMPARISON_APPROACH_FIELDS_ADJUSTMENT = [
    "Address", 
    "Proximity to Subject", 
    "Sale Price", 
    "Sale Price/Gross Liv. Area",
    "Data Source(s)", 
    "Verification Source(s)",
    "Sale or Financing Concessions Adjustment",
    "Date of Sale/Time Adjustment",
    "Location Adjustment",
    "Leasehold/Fee Simple Adjustment",
    "Site Adjustment",
    "View Adjustment",
    "Design (Style) Adjustment",
    "Quality of Construction Adjustment",
    "Actual Age Adjustment",
    "Condition Adjustment",
    "Gross Living Area Adjustment",
    "Basement & Finished Rooms Below Grade Adjustment",
    "Functional Utility Adjustment",
    "Heating/Cooling Adjustment",
    "Energy Efficient Items Adjustment",
    "Garage/Carport Adjustment",
    "Porch/Patio/Deck Adjustment",
    "Net Adjustment (Total)", 
    "Adjusted Sale Price of Comparable",
]

# RENTAL GRID
RENTAL_GRID_FIELDS = [
    "Address",
    "Proximity to Subject",
    "Date Lease Begins",
    "Date Lease Expires",
    "Monthly Rental",
    "Less: Utilities, Furniture",
    "Adjusted Monthly Rent",
    "Data Source",
    "RENT ADJUSTMENTS",
    "Rent Concessions",
    "Location/View",
    "Design and Appeal",
    "Age/Condition",
    "Total room count",
    "Bdrms count",
    "Baths count",
    "Gross Living Area",
    "Other (e.g., basement, etc.)",
    "Other:",
    "Net Adj. (total)",
]

# SALE HISTORY (MERGED)
SALE_HISTORY_FIELDS = [
    # From former Sales Transfer section
    "I ____ research the sale or transfer history of the subject property and comparable sales.(did/did not)",
    "If not, explain",
    "My research _____ reveal any prior sales or transfers of the subject property for the three years prior to the effective date of this appraisal.(did/did not)",
    "Data Source(s) for subject property research",
    "My research ______ reveal any prior sales or transfers of the comparable sales for the year prior to the date of sale of the comparable sale.(did/did not)",
    "Data Source(s) for comparable sales research",
    # From both sections
    "Analysis of prior sale or transfer history of the subject property and comparable sales",
    # From former Sale History grid
    "Date of Prior Sale/Transfer",
    "Price of Prior Sale/Transfer",
    "Data Source(s)",
    "Effective Date of Data Source(s)",
]

# RECONCILIATION
RECONCILIATION_FIELDS = [
    "Indicated Value by: Sales Comparison Approach $", 
    "Cost Approach (if developed) $", "Income Approach (if developed) $",
    "This appraisal is made ('as is', 'subject to completion per plans and specifications on the basis of a hypothetical condition that the improvements have been completed', 'subject to the following repairs or alterations on the basis of a hypothetical condition that the repairs or alterations have been completed', or 'subject to the following required inspection based on the extraordinary assumption that the condition or deficiency does not require alteration or repair:')",
    "Opinion of Market Value $",
    "Effective Date of Value"
]

ANALYSIS_COMMENTS_FIELDS = [
    "Analysis/Comments",
]

# COST APPROACH
COST_APPROACH_FIELDS = [
    # Header/Support Fields
    "Support for the opinion of site value (summary of comparable land sales or other methods for estimating site value)",
    "ESTIMATED",
    "Source of cost data",
    "Quality rating from cost service",
    "Effective date of cost data",
    # Cost Calculation Fields
    "Opinion of Site Value",
    "Dwelling",
    "Garage/Carport",
    "Total Estimate of Cost-New",
    "Depreciation",
    "Depreciated Cost of Improvements",
    "As-is Value of Site Improvements",
    "Indicated Value By Cost Approach",
    # Comments and Other Fields
    "Comments on Cost Approach (gross living area calculations, depreciation, etc.)",
    "Estimated Remaining Economic Life (HUD and VA only)",
]

INCOME_APPROACH_FIELDS = [
    "Estimated Monthly Market Rent $",
    "X Gross Rent Multiplier = $"
]

# PUD INFORMATION
PUD_INFO_FIELDS = [
    "Is the developer/builder in control of the Homeowners' Association (HOA)?", "Unit type(s)",
    "Provide the following information for PUDs ONLY if the developer/builder is in control of the HOA and the subject property is an attached dwelling unit.",
    "Legal Name of Project", "Total number of phases", "Total number of units", "Total number of units sold",
    "Total number of units rented", "Total number of units for sale", "Data source(s)", "Was the project created by the conversion of existing building(s) into a PUD?", " If Yes, date of conversion", "Does the project contain any multi-dwelling units? Yes No Data", "Are the units, common elements, and recreation facilities complete?", "If No, describe the status of completion.", "Are the common elements leased to or by the Homeowners' Association?",
    "If Yes, describe the rental terms and options.", "Describe common elements and recreational facilities."
]

# UNIFORM RESIDENTIAL APPRAISAL REPORT
UNIFORM_REPORT_FIELDS = [
    "SCOPE OF WORK:",
    "INTENDED USE:",
    "INTENDED USER:",
    "DEFINITION OF MARKET VALUE:",
    "STATEMENT OF ASSUMPTIONS AND LIMITING CONDITIONS:",
]

# CERTIFICATION
CERTIFICATION_FIELDS = [
    "Signature", "Name", "Company Name", "Company Address", "Telephone Number", "Email Address", "Date of Signature and Report",
    "Effective Date of Appraisal", "State Certification # or State License # or Other (describe)", "State # or State",
    "Expiration Date of Certification or License", "ADDRESS OF PROPERTY APPRAISED", "APPRAISED VALUE OF SUBJECT PROPERTY $",
    "LENDER/CLIENT Name",
    "Lender/Client Company Name",
    "Lender/Client Company Address",
    "Lender/Client Email Address",
]

# ADDENDUM
ADDENDUM_FIELDS = [
    "SUPPLEMENTAL ADDENDUM",
    "ADDITIONAL COMMENTS",
    "APPRAISER'S CERTIFICATION:",
    "SUPERVISORY APPRAISER'S CERTIFICATION:",
    "Analysis/Comments",
    "GENERAL INFORMATION ON ANY REQUIRED REPAIRS",
    "UNIFORM APPRAISAL DATASET (UAD) DEFINITIONS ADDENDUM",
]

# APPRAISAL AND REPORT IDENTIFICATION
APPRAISAL_ID_FIELDS = [
    "This Report is one of the following types:", 
    "Comments on Standards Rule 2-3", 
    "Reasonable Exposure Time", 
    "Comments on Appraisal and Report Identification"
]

#IMAGE
IMAGE_FIELDS =[

    "include bedroom, bed, bathroom, bath, half bath, kitchen, lobby, foyer, living room count with label and photo,please explan and match the floor plan with photo and improvement section, GLA",
    "please match comparable address in sales comparison approach and comparable photos, please make sure comp phto are not same, also find front, rear, street photo and make sure it is not same, capture any additionbal photo for adu according to check mark",
    "please match comparable address in sales comparison approach and comparable photos, please make sure comp phto are not same, also find front, rear, street photo and make sure it is not same, capture any additionbal photo for adu according to check mark, please match the same in location map, areial map should have subject address, please check signature section details of appraiser in appraiser license copy for accuracy"

]

# MARKET CONDITIONS
MARKET_CONDITIONS_FIELDS = [
    # Inventory Analysis Grid
    "Inventory Analysis Total # of Comparable Sales (Settled)",
    "Inventory Analysis Absorption Rate (Total Sales/Months)",
    "Inventory Analysis Total # of Comparable Active Listings",
    "Inventory Analysis Months of Housing Supply (Total Listings/Ab.Rate)",
    # Median Sale & List Price Grid
    "Median Sale & List Price, DOM, Sale/List % Median Comparable Sale Price",
    "Median Sale & List Price, DOM, Sale/List % Median Comparable Sales Days on Market",
    "Median Sale & List Price, DOM, Sale/List % Median Comparable List Price",
    "Median Sale & List Price, DOM, Sale/List % Median Comparable Listings Days on Market",
    "Median Sale & List Price, DOM, Sale/List % Median Sale Price as % of List Price",
    # Additional Market Fields
    "Seller-(developer, builder, etc.) paid financial assistance prevalent?",
    "Explain in detail the seller concessions trends for the past 12 months (e.g., seller contributions increased from 3% to 5%, increasing use of buydowns, closing costs, condo fees, options, etc.).",
    "Are foreclosure sales (REO sales) a factor in the market?", "If yes, explain (including the trends in listings and sales of foreclosed properties).",
    "Cite data sources for above information.",
    "Summarize the above information as support for your conclusions in the Neighborhood section of the appraisal report form. If you used any additional information, such as an analysis of pending sales and/or expired and withdrawn listings, to formulate your conclusions, provide both an explanation and support for your conclusions."
]

# CONDO
CONDO_FIELDS = [
    # Subject Project Data Grid
    "Subject Project Data Total # of Comparable Sales (Settled)",
    "Subject Project Data Absorption Rate (Total Sales/Months)",
    "Subject Project Data Total # of Comparable Active Listings",
    "Subject Project Data Months of Unit Supply (Total Listings/Ab.Rate)",
    # Additional Condo Fields
    "Are foreclosure sales (REO sales) a factor in the project?",
    "If yes, indicate the number of REO listings and explain the trends in listings and sales of foreclosed properties.",
    "Summarize the above trends and address the impact on the subject unit and project.",
]

# consistancy
consistancy = [
    "Property Address match with sales grid, subject photos address, location map, and aerial map",
    "All Comparables Address from sales grid match with photos address, location map",
    "Total Room count, bed count, bath count and GLA of improvement section match with sales grid, photos, and building sketch",
    
]

# CUSTOM ANALYSIS
CUSTOM_ANALYSIS_FIELDS = [
    "User-defined query" # This is a placeholder
]
# A dictionary to map section names to their corresponding field lists
FIELD_SECTIONS = {
    "subject": SUBJECT_FIELDS,
    "contract": CONTRACT_FIELDS,
    "neighborhood": NEIGHBORHOOD_FIELDS,
    "site": SITE_FIELDS,
    "improvements": IMPROVEMENTS_FIELDS,
    "sales_grid_adjustment": SALES_COMPARISON_APPROACH_FIELDS_ADJUSTMENT,
    "sales_grid": SALES_COMPARISON_APPROACH_FIELDS,
    "rental_grid": RENTAL_GRID_FIELDS,
    "sale_history": SALE_HISTORY_FIELDS,
    "reconciliation": RECONCILIATION_FIELDS,
    "additional_comments": ANALYSIS_COMMENTS_FIELDS,
    "cost_approach": COST_APPROACH_FIELDS,
    "income_approach": INCOME_APPROACH_FIELDS,
    "pud_info": PUD_INFO_FIELDS,
    "uniform_report": UNIFORM_REPORT_FIELDS,
    "certification": CERTIFICATION_FIELDS,
    "addendum": ADDENDUM_FIELDS,
    "appraisal_id": APPRAISAL_ID_FIELDS,
    "market_conditions": MARKET_CONDITIONS_FIELDS,
    "condo": CONDO_FIELDS,
    "image_analysis": IMAGE_FIELDS,
    "consistancy": consistancy,
    "custom_analysis": CUSTOM_ANALYSIS_FIELDS,
}

logger = logging.getLogger(__name__)

async def extract_fields_from_pdf(pdf_path, section_name: str, custom_prompt: str = None):
    # Configure the client with a longer timeout to handle large PDF processing.
    # Set a 5-minute (300 seconds) timeout.
    client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    # Get the correct field list based on the section name
    fields_to_extract = FIELD_SECTIONS.get(section_name.lower(), [])
    # Allow sections with complex prompts even if their field list is a placeholder or used differently
    if not fields_to_extract and section_name.lower() not in ['sales_grid', 'sale_history', 'improvements', 'image_analysis', 'consistancy', 'custom_analysis']:
        return {"error": f"Invalid section name provided: {section_name}"}

    prompt = "" # I've noticed you have a typo in the 'consistancy' key. It should probably be 'consistency'. I'll leave it for now to match your existing code, but you might want to correct it here and in the `FIELD_SECTIONS` dictionary.
    if section_name.lower() == 'consistancy':
        prompt = f"""
        You are an expert AI assistant specializing in real estate appraisal report review. Your task is to perform a series of consistency checks across different sections of the provided PDF document.

        Your output must be a single, valid JSON object. The keys of the JSON object must be the full text of the instructions provided in the "Consistency Checks" section below. The value for each key should be a detailed string explaining your findings for that specific instruction.

        **Consistency Checks:**

        1.  **"property address match with sales grid, subject photos, location map, and aerial map"**:
            *   **Action:** Find the subject property address in the "Subject" section. Then, find the subject property address in the "Sales Comparison Approach" grid, on any labeled "Subject Photos", on the "Location Map", and on the "Aerial Map".
            *   **Output:** Report the address found in each location and state clearly if they all match. If they do not match, list the discrepancies. For example: "Mismatch found by referring the specific section. Subject Section: 123 Main St. Sales Grid: 123 Main Street. Subject Photo: 125 Main St." or "Consistent: The address '123 Main St, Anytown, ST 12345' was found in all locations."

        2.  **"All comparables address from sales grid match with photos, location map"**:
            *   **Action:** For each comparable property in the "Sales Comparison Approach" grid, extract its address. Then, find the corresponding comparable property photos and the "Location Map". Verify that the address on the photo labels and the location map matches the address from the grid.
            *   **Output:** Report on each comparable. For example: "Comp 1: Match. Address '456 Oak Ave' is consistent across grid, photo, and map. Comp 2: Mismatch. Address is '789 Pine Ln' in grid but '798 Pine Ln' on photo label."

        3.  **"Total Room count, bed count, bath count and GLA of improvement section match with sales grid, photos, and building sketch"**:
            *   **Action:** First, locate the "Building Sketch" or "Floor Plan". Carefully read all labels and dimensions on it. Count the number of bedrooms, bathrooms (full and half), and total rooms directly from the sketch. Calculate the Gross Living Area (GLA) from the dimensions provided on the sketch if possible. Then, find the corresponding values for the subject property in the "Improvements" section and the "Sales Comparison Approach" grid. Also, review any interior photos to visually confirm room types.
            *   **Output:** Provide a detailed comparison of the findings from each source (Sketch, Improvements Section, Sales Grid, Photos). Explicitly state the values from each location. If there is a mismatch, identify it clearly. For example: "GLA Mismatch: Building Sketch shows 1,820 sq. ft. (calculated from dimensions 40'x45.5'), but Improvements section lists 1,850 sq. ft. Bedroom count is consistent at 3 across all sections. Bathroom count from sketch is 2.5, matching the Improvements section."

        **Example of the final JSON structure:**
        {{
            "property address match with sales grid, subject photos address, location map, and aerial map": "Consistent: The address '456 Oak Avenue, Pleasantville, ST 54321' was found consistently in the Subject section, Sales Grid, Location Map, and on a Subject Photo label.",
            "All comparables address from sales grid match with comparable photos address, location map": "Comp 1: Match. Address '111 Maple St' is consistent. Comp 2: Match. Address '222 Birch Rd' is consistent.",
            "Total Room count, bed count, bath count and GLA of improvement section match with sales grid, photos, and building sketch": "GLA is consistent at 2,100 sq. ft. across Improvements, Sales Grid, and Building Sketch. Bedroom count is consistent at 4. Bathroom count is consistent at 2.5."
        }}
        """
        # The fields_to_extract list is used as the keys in the final JSON, so we ensure it's set correctly for this section.
        fields_to_extract = consistancy

    if section_name.lower() == 'subject':
        prompt = f"""
        You are an expert at extracting information from the "Subject" section of a real estate appraisal report.
        Analyze the provided PDF document and extract the values for all fields listed below.

        Your output must be a single, valid JSON object where the keys are the field names and the values are the extracted data.

        **Instructions:**
        1.  **Be Thorough:** Extract data for every field listed.
        2.  **Use Null for Missing Data:** If a field is not found, is not applicable, or has no value (e.g., '--', 'N/A', or blank), use `null` as its value. Do not invent data.
        3.  **Handle Complex Fields:**
            *   For fields represented by checkboxes (e.g., "PUD"), if the checkbox is marked/selected, extract "Yes". If it is not marked/selected, extract "No".
            *   For yes/no questions like "Offered for Sale in Last 12 Months", extract the "Yes" or "No" answer. The subsequent field "Report data source(s) used, offering price(s), and date(s)" should contain the corresponding explanation if the answer was "Yes". If the answer is "No", the explanation field should be `null`.
            *   If "PUD" is marked as "Yes", then the fields "HOA $" and "HOA(per year/per month)" must be extracted. If "PUD" is "No", these HOA-related fields should be `blank`.
        **Fields to Extract:**
        {json.dumps(fields_to_extract, indent=2)}

        **Example of the final JSON structure:**
        {{
            "Property Address": "123 Main St",
            "City": "Anytown",
            "County": "Sample County",
            "State": "CA",
            "Zip Code": "12345",
            "Borrower": "John Doe",
            "Assignment Type": "Purchase Transaction",
            "Offered for Sale in Last 12 Months": "No",
            "Report data source(s) used, offering price(s), and date(s)": null,
            "PUD": "Yes",
            "...": "..." 
        }}
        """
    elif section_name.lower() == 'sale_history':
        prompt = f"""
        You are an expert at extracting information from appraisal reports, focusing on the "Sale or Transfer History" section.
        This section contains both general statements about research and a grid detailing prior sales for the subject and comparables.

        Your output must be a single, valid JSON object.

        The JSON object must contain the following top-level keys:
        1.  `"subject"`: A JSON object for the subject property's sale history grid data.
        2.  `"comparables"`: A JSON array of objects, one for each comparable property's sale history grid data.
        3.  All other fields from the "Fields to Extract" list below should be top-level keys in the JSON object.

        **Instructions:**
        1.  **Grid Data:** For the subject and each comparable, extract the prior sale details into the `subject` and `comparables` objects. If a property has multiple prior sales, extract the most recent one. Maintain the original sequence of comparables.
        2.  **General Statements:** Extract the text for the general research statements and analysis as top-level key-value pairs.
        3.  **Handle (did/did not):** For fields with "(did/did not)", extract only the selected word ("did" or "did not").
        4.  **Use Null for Missing Data:** If any field, grid cell, or value is not found, is blank, or is not applicable, use `null` as its value.

        **Fields to Extract:**
        {json.dumps(fields_to_extract, indent=2)}

        **Example of the final JSON structure:**
        {{
            "I ____ research the sale or transfer history...": "did",
            "My research _____ reveal any prior sales or transfers of the subject property...": "did not",
            "subject": {{
                "Date of Prior Sale/Transfer": "01/15/2021",
                "Price of Prior Sale/Transfer": "$450,000",
                "Effective Date of Data Source(s)": "01/15/2021"
            }},
            "comparables": [
                {{ "Date of Prior Sale/Transfer": null, "Price of Prior Sale/Transfer": null, ... }}
            ],
            "Analysis of prior sale or transfer history of the subject property and comparable sales": "The subject property was not sold in the last three years. Comp 1 sold 11 months ago..."
        }}"""
    elif section_name.lower() == 'improvements':
        prompt = f"""
        You are an expert at extracting information from the "Improvements" section of an appraisal report.
        Analyze the provided PDF document and extract the values for all fields listed below.

        Your output must be a single, valid JSON object where the keys are the field names and the values are the extracted data.

        **Instructions:**
        1.  **Be Thorough:** Extract data for every field listed.
        2.  **Use Null for Missing Data:** If a field is not found, is not applicable, or has no value (e.g., '--', 'N/A', or blank), use `null` as its value. Do not invent data.
        3.  **Handle Complex Fields:**
            *   For fields like "Appliances", list all items that are checked or mentioned (e.g., "Refrigerator, Range/Oven, Dishwasher").
            *   For fields with "(Material/Condition)", capture both aspects if available (e.g., "Brick/Good").
            *   For yes/no questions, extract the "Yes" or "No" answer. The subsequent "If Yes, describe" or "If No, describe" fields should contain the corresponding explanation.
            *   For field like "Basement Finish", value 0 or more than 0 %
            *   Handle checkboxs in general description

        **Fields to Extract:**
        {json.dumps(fields_to_extract, indent=2)}

        **Example of the final JSON structure:**
        {{
            "Units": "1",
            "Year Built": "1995",
            "Exterior Walls (Material/Condition)": "Vinyl Siding/Average",
            "Appliances (Refrigerator,Range/Oven, Dishwasher, Disposal, Microwave, Washer/Dryer, Other (describe))": "Refrigerator, Range/Oven, Dishwasher",
            "Are there any physical deficiencies or adverse conditions that affect the livability, soundness, or structural integrity of the property?": "No",
            "If Yes, describe": null,
            "Does the property generally conform to the neighborhood (functional utility, style, condition, use, construction, etc.)?": "Yes",
            "If No, describe": null,
            "Square Feet of Gross Living Area Above Grade": "1850",
            "...": "..."
        }}
        """
    elif section_name.lower() == 'neighborhood':
        prompt = f"""
        You are an expert at extracting information from the "Neighborhood" section of a real estate appraisal report.
        Analyze the provided PDF document and extract the values for all fields listed below.

        Your output must be a single, valid JSON object where the keys are the field names and the values are the extracted data.

        **Instructions:**
        1.  **Be Thorough:** Extract data for every field listed.
        2.  **Use Null for Missing Data:** If a field is not found, is not applicable, or has no value (e.g., '--', 'N/A', or blank), use `null` as its value.
        3.  **Conditional Extraction for "Other" Land Use:**
            *   First, find the percentage value for the "Other" field in the "Present Land Use" table.
            *   **If and only if this percentage is greater than 0%**, you must find the description for this "Other" category (e.g., "Vacant", "Garden", "Open Space") and extract it into the "Present Land Use Other Description" field.
            *   If the "Other" percentage is 0% or not present, the "Present Land Use Other Description" field must be `null`.

        **Fields to Extract:**
        {json.dumps(fields_to_extract, indent=2)}

        **Example of the final JSON structure:**
        {{
            "Location": "Urban",
            "Property Values": "Stable",
            "One-Unit": "85%",
            "2-4 Unit": "5%",
            "Multi-Family": "5%",
            "Commercial": "0%",
            "Other": "5%",
            "Present Land Use Other Description": "Primarily vacant residential lots.",
            "Neighborhood Description": "The neighborhood is a well-established residential area...",
            "...": "..."
        }}
        """
    elif section_name.lower() == 'contract':
        prompt = f"""
        You are an expert at extracting information from the "Contract" section of a real estate appraisal report.
        Analyze the provided PDF document and extract the values for all fields listed below.

        Your output must be a single, valid JSON object where the keys are the field names and the values are the extracted data.

        **Instructions:**
        1.  **Be Thorough:** Extract data for every field listed.
        2.  **Use Null for Missing Data:** If a field is not found, is not applicable, or has no value (e.g., '--', 'N/A', or blank), use `null` as its value. Do not invent data.
        3.  **Handle Complex Fields:**
            *   For the field "I _____ analyze the contract for sale for the subject purchase transaction.", find the checkbox for "did" or "did not". Extract only the selected word ("did" or "did not") as the value for this field.
            *   For the separate field "Explain the results of the analysis of the contract for sale or why the analysis was not performed.", extract the full text explanation. If the analysis "did not" happen, this field should contain the reason why. If it "did" happen, it should contain the results.
            *   For yes/no questions, extract the "Yes" or "No" answer.

        **Fields to Extract:**
        {json.dumps(fields_to_extract, indent=2)}

        **Example of the final JSON structure:**
        {{
            "I _____ analyze the contract for sale for the subject purchase transaction.": "did",
            "Explain the results of the analysis of the contract for sale or why the analysis was not performed.": "The contract is dated 05/15/2024 for a price of $550,000. No concessions were noted.",
            "Contract Price $": "550,000",
            "Is there any financial assistance (loan charges, sale concessions, gift or downpay i etc.) to be paid by any party on behalf of the borrower?(Yes/No)": "No",
            "If Yes, report the total dollar amount and describe the items to be paid.": null,
            "...": "..."
        }}
        """
    elif section_name.lower() == 'site':
        prompt = f"""
        You are an expert at extracting information from the "Site" section of a real estate appraisal report.
        Analyze the provided PDF document and extract the values for all fields listed below.

        Your output must be a single, valid JSON object where the keys are the field names and the values are the extracted data.

        **Instructions:**
        1.  **Be Thorough:** Extract data for every field listed.
        2.  **Use Null for Missing Data:** If a field is not found, is not applicable, or has no value (e.g., '--', 'N/A', or blank), use `null` as its value. Do not invent data.
        3.  **Handle Complex Fields:**
            *   For yes/no questions, extract the "Yes" or "No" answer.
            *   For the field "Are there any adverse site conditions...", if the answer is "Yes", you must extract the explanation into the "If Yes, describe" field. If the answer is "No", the "If Yes, describe" field should be `null`.
            *   For fields like "Zoning Compliance", extract the specific classification (e.g., "Legal", "Legal Nonconforming", "Illegal", "No Zoning").

            *   For utility fields ("Electricity", "Gas", "Water", "Sanitary Sewer"), if "Other" is selected, you must include the accompanying description (e.g., "Other - Solar", "Other - Septic"). If no description is provided with "Other", extract just "Other".

        **Fields to Extract:**
        {json.dumps(fields_to_extract, indent=2)}

        **Example of the final JSON structure:**
        {{
            "Dimensions": "80x120",
            "Area": "9,600 Sq. Ft.",
            "Zoning Compliance": "Legal",
            "Is the highest and best use of subject property as improved (or as proposed per plans and specifications) the present use?": "Yes",
            "FEMA Special Flood Hazard Area": "No",
            "FEMA Flood Zone": "X",
            "Are there any adverse site conditions or external factors (easements, encroachments, environmental conditions, land uses, etc.)?": "Yes",
            "If Yes, describe": "Minor utility easement noted along the rear property line. No adverse impact observed.",
            "Street": "Public/Asphalt",
            "...": "..."
        }}
        """
    elif section_name.lower() == 'image_analysis':
        prompt = f"""
        You are an expert AI assistant specializing in the detailed analysis of photos and maps within real estate appraisal reports.
        Analyze the provided PDF document, focusing on all images, maps, and signatures. Your task is to perform a series of verification and cross-referencing tasks based on the instructions below.

        Your output must be a single, valid JSON object. The keys of the JSON object must be the full text of the instructions provided in the "Analysis Instructions" section below. The value for each key should be a detailed string explaining your findings for that specific instruction.

        **Analysis Instructions:**

        1.  **"include bedroom, bed, bathroom, bath, half bath, kitchen, lobby, foyer, living room count with label and photo,please explain and match the floor plan with photo and improvement section, GLA"**
            *   **Action:** First, locate the "Building Sketch" or "Floor Plan". Carefully read all room labels and dimensions. Count the number of bedrooms, bathrooms (full and half), kitchens, etc., directly from the sketch. Calculate the Gross Living Area (GLA) from the sketch's dimensions. Next, find all interior photos and identify the room type for each. Finally, compare the counts and GLA from the sketch and photos with the data in the "Improvements" section and the "Sales Comparison Approach" grid.
            *   **Output:** A detailed summary of the room counts and GLA from each source (Sketch, Photos, Improvements section). Clearly state the values from each location and highlight any discrepancies. For example: "Sketch shows 3 bedrooms, 2.5 baths, and 1820 sq. ft. GLA. Photos confirm 3 bedrooms and a kitchen. Improvements section lists 3 beds, 2.5 baths, and 1850 sq. ft. GLA. A mismatch of 30 sq. ft. in GLA was found."

        2.  **"please match comparable address in sales comparison approach and comparable photos, please make sure comp photo are not same, also find front, rear, street photo and make sure it is not same, capture any additional photo for adu according to check mark"**
            *   **Action:** Locate the photos for each comparable property. For each one, verify that the address shown in the photo's label matches the address in the "Sales Comparison Approach" grid. Confirm that the photos for different comparables are unique and not duplicates. Identify the "Front", "Rear", and "Street" view photos for the subject property and confirm they are distinct images. If an Accessory Dwelling Unit (ADU) is mentioned or checked in the report, find and note any photos of it.
            *   **Output:** A report on the address matching for each comparable, confirmation of photo uniqueness, and findings on ADU photos.

        3.  **"please match comparable address in sales comparison approach and comparable photos, please make sure comp photo are not same, also find front, rear, street photo and make sure it is not same, capture any additional photo for adu according to check mark, please match the same in location map, aerial map should have subject address, please check signature section details of appraiser in appraiser license copy for accuracy"**
            *   **Action:** Perform all checks from instruction #2. Additionally, locate the "Location Map" and verify that the comparable properties are correctly plotted. Find the "Aerial Map" and confirm the subject property's address is labeled on it. Finally, locate the appraiser's signature and license details in the "Certification" section and compare them for accuracy against any image of the appraiser's license found elsewhere in the document.
            *   **Output:** A comprehensive summary covering all points from instruction #2, plus the results of the location map check, aerial map verification, and the signature/license comparison.

        **Example of the final JSON structure:**
        {{
            "include bedroom, bed, bathroom, bath, half bath, kitchen, lobby, foyer, living room count with label and photo,please explain and match the floor plan with photo and improvement section, GLA": "Analysis result for instruction 1...",
            "please match comparable address in sales comparison approach and comparable photos, please make sure comp photo are not same, also find front, rear, street photo and make sure it is not same, capture any additional photo for adu according to check mark": "Analysis result for instruction 2...",
            "please match comparable address in sales comparison approach and comparable photos, please make sure comp photo are not same, also find front, rear, street photo and make sure it is not same, capture any additional photo for adu according to check mark, please match the same in location map, aerial map should have subject address, please check signature section details of appraiser in appraiser license copy for accuracy": "Analysis result for instruction 3..."
        }}
        """
    elif section_name.lower() == 'sales_grid':
        prompt = f"""
        You are an expert at extracting information from appraisal reports, focusing on the Sales Comparison Approach grid.
        Analyze the provided PDF document to extract data for the Subject property, all Comparable properties, and the summary/history fields related to the sales comparison approach.
        
        Your output must be a single, valid JSON object with the following top-level keys:
        1.  `"subject"`: A JSON object for the subject property.
        2.  `"comparables"`: A JSON array of objects, one for each comparable property.
        3.  `"Indicated Value by Sales Comparison Approach"`: The final indicated value.

        **Instructions:**
        1.  **Extract All Comparables:** You must find and extract data for **all** comparable properties in the grid. Maintain their original sequence.
        2.  **Use Null for Missing Data:** If a field is not found, is blank, or has no value (e.g., '--', 'N/A'), use `null` as its value.
        3.  **Handle Adjustments Accurately:**
            *   For all fields ending in "Adjustment", extract the precise monetary value.
            *   Negative values are often shown in parentheses, like `($2,000)`. You must extract these with a negative sign, like `-$2,000`.
            *   Positive values may or may not have a `+` sign.
            *   If an adjustment is `$0` or blank, extract it as such.
        4.  **Handle Complex Text:** For fields like "Basement & Finished Rooms Below Grade", capture the entire text value (e.g., "1000sf / 500sf Rec Room").

        **Fields for Subject and each Comparable:**
        {json.dumps(fields_to_extract, indent=2)}

        **Example of a comparable's adjustment field:**
        "Condition Adjustment": "-$5,000"
        """
    elif section_name.lower() == 'rental_grid':
        prompt = f"""
        You are an expert at extracting information from appraisal reports, focusing on the Rental Comparison grid.
        Analyze the provided PDF document to extract data for the Subject property, all Comparable rental properties, and the summary fields at the bottom of the section.

        Your output must be a single, valid JSON object with the following top-level keys:
        1.  `"subject"`: A JSON object for the subject property's rental data.
        2.  `"comparables"`: A JSON array of objects, one for each comparable rental property.
        3.  `"Indicated Monthly Market Rent"`: The final indicated monthly market rent for the subject.
        4.  `"Comments on market data..."`: The full text of the comments on market data, including vacancy, trends, and support for adjustments.
        5.  `"Final Reconciliation of Market Rent:"`: The full text of the final reconciliation of market rent.

        **Instructions:**
        1.  **Extract All Comparables:** You must find and extract data for **all** comparable rental properties in the grid. Maintain their original sequence.
        2.  **Use Null for Missing Data:** If a field is not found, is blank, or has no value (e.g., '--', 'N/A'), use `null` as its value.
        3.  **Handle Adjustments:** For adjustment fields (like "Rent Concessions", "Location/View", etc.), extract the precise monetary value. Negative values are often in parentheses, like `($50)`; extract these with a negative sign, like `-$50`.

        **Fields for Subject and each Comparable:**
        {json.dumps(fields_to_extract, indent=2)}

        **Example of the final JSON structure:**
        {{
            "subject": {{ "Address": "123 Main St", "Monthly Rental": null, "Location/View": null, ... }},
            "comparables": [
                {{ "Address": "456 Oak Ave", "Monthly Rental": "$2,500", "Location/View": "-$50", ... }},
                {{ "Address": "789 Pine Ln", "Monthly Rental": "$2,400", "Location/View": "$0", ... }}
            ],
            "Indicated Monthly Market Rent": "$2,450",
            "Comments on market data...": "The rental market is stable with low vacancy rates (estimated at 3%). Rents have been increasing slightly over the past year. Adjustments are based on market data from the local MLS.",
            "Final Reconciliation of Market Rent:": "After considering all comparables and giving most weight to Comp 2 due to its similarity, the market rent is reconciled to $2,450 per month."
        }}
        """

    elif section_name.lower() == 'sales_grid_adjustment':
        prompt = f"""
        You are an expert AI assistant specializing in real estate appraisal review. Your task is to analyze the Sales Comparison Approach grid for adjustment consistency.
        Analyze the provided PDF document to extract data for the Subject property and all Comparable properties, and then provide a summary of adjustment consistency.

        Your output must be a single, valid JSON object with the following top-level keys:
        1.  `"subject"`: A JSON object for the subject property's data from the grid.
        2.  `"comparables"`: A JSON array of objects, one for each comparable property.
        3.  `"adjustment_analysis"`: A JSON object containing your analysis of the adjustments. This object should have two keys:
            *   `"summary"`: A high-level summary of your findings (e.g., "Adjustments appear consistent," or "Inconsistencies found in Condition and GLA adjustments.").
            *   `"details"`: An array of strings, where each string is a detailed explanation of a specific finding (consistent or inconsistent).

        **Instructions:**
        1.  **Extract Data:** For the subject and each comparable, extract all fields listed below. If a field is blank, empty, or not applicable (e.g., '--'), use `null` as its value. Pay close attention to negative adjustments in parentheses.
        2.  **Analyze Consistency:** After extracting the data, compare the adjustments across all comparables. An adjustment is consistent if the same dollar amount is applied for the same feature difference from the subject. For example, if Comp 1 and Comp 2 both have a "Superior" view compared to the subject's "Average" view, their "View Adjustment" should be identical.
        3.  **Report Findings:** In the `"details"` array, report your findings.
            *   For **consistent** adjustments, state it clearly. Example: "View Adjustment: Consistent. A -$5,000 adjustment was applied to all comparables with a 'Superior' view."
            *   For **inconsistent** adjustments, describe the discrepancy. Example: "Condition Adjustment: Inconsistent. Comp 1 received a -$3,000 adjustment for 'Average' condition, while Comp 3 received a -$5,000 adjustment for the same 'Average' condition."
            *   Mention adjustments that were not needed (all comps matched the subject).

        **Fields to Extract for Subject and each Comparable:**
        {json.dumps(fields_to_extract, indent=2)}

        **Example of the final JSON structure:**
        {{
            "subject": {{ "Address": "123 Main St", "Condition": "Good", "Gross Living Area": "1850", ... }},
            "comparables": [
                {{ "Address": "456 Oak Ave", "Condition": "Average", "Condition Adjustment": "-$3,000", ... }},
                {{ "Address": "789 Pine Ln", "Condition": "Good", "Condition Adjustment": "$0", ... }},
                {{ "Address": "101 Maple Dr", "Condition": "Average", "Condition Adjustment": "-$5,000", ... }}
            ],
            "adjustment_analysis": {{
                "summary": "Inconsistencies found in Condition adjustments.",
                "details": [
                    "Condition Adjustment: Inconsistent. Comp 1 received a -$3,000 adjustment for 'Average' condition, while Comp 3 received a -$5,000 adjustment for the same 'Average' condition.",
                    "GLA Adjustment: Consistent. A rate of $50/sq. ft. was applied across all comparables.",
                    "Location Adjustment: Not applied. All comparables were in a similar location to the subject."
                ]
            }}
        }}
        """
    elif section_name.lower() == 'market_conditions':
        prompt = f"""
        You are an expert at extracting information from the "Market Conditions" addendum (Form 1004MC) of a real estate appraisal report.
        Analyze the provided PDF document and extract the values for all fields listed below.

        Your output must be a single, valid JSON object.

        **Instructions:**
        1.  **Handle Grid Data:** For fields that represent a row in the Market Conditions grid (e.g., "Inventory Analysis Total # of Comparable Sales (Settled)"), create a nested JSON object. The keys of this nested object should be the time periods ("Prior 7–12 Months", "Prior 4–6 Months", "Current – 3 Months", "Overall Trend"), and the values should be the data from the corresponding cells in the grid. For the "Overall Trend" column, extract the text of the selected checkbox (e.g., "Increasing", "Decreasing", "Stable").
        2.  **Handle Yes/No Questions:** For yes/no questions, extract the "Yes" or "No" answer. The subsequent explanation field (e.g., "If yes, explain...") should contain the corresponding text. If the answer is "No", the explanation field should be `null`.
        3.  **Use Null for Missing Data:** If any field or grid cell is not found, is not applicable, or has no value (e.g., '--', 'N/A', or blank), use `null` as its value. Do not invent data.

        **Fields to Extract:**
        {json.dumps(fields_to_extract, indent=2)}

        **Example of the final JSON structure:**
        {{
            "Inventory Analysis Total # of Comparable Sales (Settled)": {{
                "Prior 7–12 Months": "150",
                "Prior 4–6 Months": "80",
                "Current – 3 Months": "45",
                "Overall Trend": "Decreasing"
            }},
            "Median Sale & List Price, DOM, Sale/List % Median Comparable Sale Price": {{
                "Prior 7–12 Months": "$500,000",
                "Prior 4–6 Months": "$510,000",
                "Current – 3 Months": "$515,000",
                "Overall Trend": "Increasing"
            }},
            "Are foreclosure sales (REO sales) a factor in the market?": "Yes",
            "If yes, explain (including the trends in listings and sales of foreclosed properties).": "REO sales make up 5% of the market, a trend that has been stable over the last 6 months.",
            "Summarize the above information as support for your conclusions in the Neighborhood section...": "The market shows increasing prices despite a decrease in sales volume, indicating strong demand and limited inventory...",
            "...": "..."
        }}
        """
    elif section_name.lower() == 'condo':
        prompt = f"""
        You are an expert at extracting information from the "Project Information" section for condominiums in a real estate appraisal report.
        Analyze the provided PDF document and extract the values for all fields listed below.

        Your output must be a single, valid JSON object.

        **Instructions:**
        1.  **Handle Grid Data:** For fields that represent a row in the "Subject Project Data" grid (e.g., "Subject Project Data Total # of Comparable Sales (Settled)"), create a nested JSON object. The keys of this nested object should be the time periods ("Prior 7–12 Months", "Prior 4–6 Months", "Current – 3 Months", "Overall Trend"), and the values should be the data from the corresponding cells in the grid. For the "Overall Trend" column, extract the text of the selected checkbox (e.g., "Increasing", "Decreasing", "Stable").
        2.  **Handle Yes/No Questions:** For yes/no questions, extract the "Yes" or "No" answer. The subsequent explanation field (e.g., "If yes, indicate...") should contain the corresponding text. If the answer is "No", the explanation field should be `null`.
        3.  **Use Null for Missing Data:** If any field or grid cell is not found, is not applicable, or has no value (e.g., '--', 'N/A', or blank), use `null` as its value. Do not invent data.

        **Fields to Extract:**
        {json.dumps(fields_to_extract, indent=2)}

        **Example of the final JSON structure:**
        {{
            "Subject Project Data Total # of Comparable Sales (Settled)": {{
                "Prior 7–12 Months": "25",
                "Prior 4–6 Months": "15",
                "Current – 3 Months": "10",
                "Overall Trend": "Decreasing"
            }},
            "Subject Project Data Absorption Rate (Total Sales/Months)": {{
                "Prior 7–12 Months": "4.2",
                "Prior 4–6 Months": "5.0",
                "Current – 3 Months": "3.3",
                "Overall Trend": "Stable"
            }},
            "Are foreclosure sales (REO sales) a factor in the project?": "No",
            "If yes, indicate the number of REO listings and explain the trends in listings and sales of foreclosed properties.": null,
            "Summarize the above trends and address the impact on the subject unit and project.": "The project shows stable absorption despite a decrease in sales volume. Foreclosures are not a significant factor.",
            "...": "..."
        }}
        """
    elif section_name.lower() == 'cost_approach':
        prompt = f"""You are an expert at extracting information from the "Cost Approach" section of a real estate appraisal report.
        Analyze the provided PDF document and extract the values for all fields listed below.

        Your output must be a single, valid JSON object where the keys are the field names and the values are the extracted data.

        **Instructions:**
        1.  **Be Thorough:** Extract data for every field listed. This includes supporting text fields, the main cost calculation table, and additional comments.
        2.  **Use Null for Missing Data:** If a field is not found, is not applicable, or has no value (e.g., '--', 'N/A', or is blank), use `null` as its value. Do not invent data.
        3.  **Handle Monetary Values:** For fields representing costs or values (e.g., "Opinion of Site Value", "Dwelling", "Indicated Value By Cost Approach"), extract the full monetary value, including any currency symbols or commas (e.g., "$120,000").
        4.  **Handle Descriptive Text:** For descriptive fields (e.g., "Support for the opinion of site value...", "Comments on Cost Approach..."), extract the complete text content.
        5.  **Handle the "ESTIMATED" field:** The word "ESTIMATED" often appears as a header for the cost calculation table. If you find this word, extract it as the value for the "ESTIMATED" field. If it's not present, use `null`.

        **Fields to Extract:**
        {json.dumps(fields_to_extract, indent=2)}

        **Example of the final JSON structure:**
        {{
            "Support for the opinion of site value (summary of comparable land sales or other methods for estimating site value)": "Based on analysis of three comparable land sales in the subject's market area.",
            "ESTIMATED": "ESTIMATED",
            "Source of cost data": "Marshall & Swift",
            "Quality rating from cost service": "Average",
            "Effective date of cost data": "01/2024",
            "Opinion of Site Value": "$100,000",
            "Dwelling": "$350,000",
            "Garage/Carport": "$25,000",
            "Total Estimate of Cost-New": "$475,000",
            "Depreciation": "$50,000",
            "Depreciated Cost of Improvements": "$425,000",
            "As-is Value of Site Improvements": "$10,000",
            "Indicated Value By Cost Approach": "$535,000",
            "Comments on Cost Approach (gross living area calculations, depreciation, etc.)": "Depreciation estimated using the age-life method. GLA calculations are consistent with the building sketch.",
            "Estimated Remaining Economic Life (HUD and VA only)": "50 Years"
        }}
        """
    elif section_name.lower() == 'custom_analysis':
        if not custom_prompt:
            return {} # Return empty dict if no prompt; view handles rendering the form page.
        prompt = f"""You are an expert AI assistant specializing in real estate appraisal report analysis. A user has provided a PDF document and a specific query.
        Analyze the entire PDF document thoroughly to answer the user's query.

        **User's Query:**
        "{custom_prompt}"

        **Your Task:**
        Provide a structured and comprehensive answer to the user's query based on the content of the PDF.
        Format your response as a single, valid JSON object with the following keys:

        1.  `"query_summary"`: A brief, one-sentence summary of the user's original query.
        2.  `"findings"`: A JSON array of objects. Each object should represent a specific data point or piece of evidence found in the document that relates to the query. Each object in the array should have these keys:
            *   `"finding_title"`: A short, descriptive title for the finding (e.g., "GLA in Improvements Section", "Comparable 1 Address").
            *   `"finding_detail"`: The specific data or text extracted from the document (e.g., "1,850 sq. ft.", "123 Oak St").
            *   `"source_location"`: The section or page number where this information was found (e.g., "Improvements Section, Page 3", "Sales Grid").
        3.  `"analysis_summary"`: A short summary that synthesizes the findings and directly answers the user's query as corrcted or not corrected, addressed or not addressed. Give reference of addedum page where comment is present along with section where it is corrected.Also highlight any deviation with respect to corrected revision if you disagree.

        **Example for query "Check GLA consistency":**
        {{
            "query_summary": "Checking for discrepancies in Gross Living Area (GLA) across the report.",
            "findings": [
                {{
                    "finding_title": "GLA in Improvements Section",
                    "finding_detail": "1,850 sq. ft.",
                    "source_location": "Improvements, Page 2"
                }},
                {{
                    "finding_title": "GLA in Sales Grid (Subject)",
                    "finding_detail": "1,850 sq. ft.",
                    "source_location": "Sales Comparison Approach"
                }}
            ],
            "analysis_summary": "The Gross Living Area (GLA) is consistently reported as 1,850 sq. ft. in both the Improvements section and the Sales Comparison Approach grid. No discrepancies were found."
        }}
        """

    elif section_name.lower() == 'reconciliation':
        prompt = f"""
        You are an expert at extracting information from the "Reconciliation" section of a real estate appraisal report.
        Analyze the provided PDF document and extract the values for all fields listed below.

        Your output must be a single, valid JSON object where the keys are the field names and the values are the extracted data.

        **Instructions:**
        1.  **Be Thorough:** Extract data for every field listed.
        2.  **Use Null for Missing Data:** If a field is not found, is not applicable, or has no value, use `null` as its value.
        3.  **Specific Extraction for Market Value:**
            *   Find the long sentence that states "...my (our) opinion of the market value... is $_______, as of ________...".
            *   From this sentence, extract only the dollar amount (e.g., "550,000") into the `"Opinion of Market Value $"` field.
            *   Extract the date (e.g., "05/20/2024") into the `"Effective Date of Value"` field.

        **Fields to Extract:**
        {json.dumps(fields_to_extract, indent=2)}

        **Example of the final JSON structure:**
        {{
            "Indicated Value by: Sales Comparison Approach $": "550,000",
            "Opinion of Market Value $": "550,000",
            "Effective Date of Value": "05/20/2024",
            "...": "..."
        }}
        """
    else:
        prompt = f"""
        You are an expert at extracting information from appraisal reports.
        Analyze the provided PDF document and extract the values for the following fields for the '{section_name}' section.
        Return the result as a single, valid JSON object. The keys of the JSON object should be the field names,
        and the values should be the extracted data from the document.
        If a field is not found or its value cannot be determined, use `null` as its value.

        Fields to extract:
        {json.dumps(fields_to_extract, indent=2)}
        """
    

    try:
        # Use asyncio.to_thread to run synchronous code in an async function
        uploaded_file = await asyncio.to_thread(
            client.files.upload,
            file=pdf_path
        )

        # Wait for the file to be active.
        while uploaded_file.state.name == "PROCESSING":
            logger.info(f"Waiting for file {uploaded_file.name} to be processed...")
            # Use asyncio.sleep in an async function
            await asyncio.sleep(10)
            # Fetch the latest status of the file.
            uploaded_file = await asyncio.to_thread(client.files.get, name=uploaded_file.name)

        if uploaded_file.state.name != "ACTIVE":
            logger.error(f"File {uploaded_file.name} is not in an ACTIVE state. Current state: {uploaded_file.state.name}")
            return {"error": f"File processing failed. The file is in state: {uploaded_file.state.name}"}

        logger.info(f"File {uploaded_file.name} is now ACTIVE and ready for use.")

        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=[uploaded_file, prompt],
        )

        # The model's response text should be a JSON string. We parse it into a Python dict.
        # We also clean up potential markdown code fences.
        cleaned_text = response.text.strip().lstrip("```json").rstrip("```")
        return json.loads(cleaned_text)

    except (google_exceptions.GoogleAPIError, json.JSONDecodeError, Exception) as e:
        logger.error(f"An error occurred during PDF extraction: {e}", exc_info=True)
        # Return an error dictionary that can be displayed to the user
        return {"error": f"An error occurred during extraction: {str(e)}"}