import re

def convert_md_to_txt(md_content):
    # Remove Markdown formatting for plain text
    txt_content = re.sub(r'(\*\*|__)(.*?)\1', r'\2', md_content)  # Bold
    txt_content = re.sub(r'(\*|_)(.*?)\1', r'\2', txt_content)    # Italic
    txt_content = re.sub(r'`(.*?)`', r'\1', txt_content)          # Inline code
    txt_content = re.sub(r'!\[.*?\]\(.*?\)', '', txt_content)     # Images
    txt_content = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', txt_content)   # Links
    txt_content = re.sub(r'#+ (.*?)\n', r'\1\n\n', txt_content)   # Headers with extra newlines
    txt_content = re.sub(r'\n\s*\n', '\n\n', txt_content)         # Ensure single newlines are double newlines
    return txt_content

def convert_md_to_bbcode(md_content):
    # Convert Markdown to BBCode
    bbcode_content = re.sub(r'(\*\*|__)(.*?)\1', r'[b]\2[/b]', md_content)  # Bold
    bbcode_content = re.sub(r'(\*|_)(.*?)\1', r'[i]\2[/i]', bbcode_content) # Italic
    bbcode_content = re.sub(r'`(.*?)`', r'[code]\1[/code]', bbcode_content) # Inline code
    bbcode_content = re.sub(r'!\[.*?\]\((.*?)\)', r'[img]\1[/img]', bbcode_content) # Images
    bbcode_content = re.sub(r'\[(.*?)\]\((.*?)\)', r'[url=\2]\1[/url]', bbcode_content) # Links

    # Headers with decreasing sizes, extra newlines, and bold
    bbcode_content = re.sub(r'###### (.*?)\n', r'\n[size=1][b]\1[/b][/size]\n', bbcode_content) # H6
    bbcode_content = re.sub(r'##### (.*?)\n', r'\n[size=2][b]\1[/b][/size]\n', bbcode_content)  # H5
    bbcode_content = re.sub(r'#### (.*?)\n', r'\n[size=3][b]\1[/b][/size]\n', bbcode_content)   # H4
    bbcode_content = re.sub(r'### (.*?)\n', r'\n[size=4][b]\1[/b][/size]\n', bbcode_content)    # H3
    bbcode_content = re.sub(r'## (.*?)\n', r'\n[size=5][b]\1[/b][/size]\n', bbcode_content)     # H2
    bbcode_content = re.sub(r'# (.*?)\n', r'\n[size=6][b]\1[/b][/size]\n', bbcode_content)      # H1

    # Convert plaintext blocks to BBCode code blocks
    bbcode_content = re.sub(r'```plaintext\n(.*?)\n```', r'[code]\1[/code]', bbcode_content, flags=re.DOTALL)

    return bbcode_content

def convert_readme(input_file, txt_output_file, bbcode_output_file):
    with open(input_file, 'r', encoding='utf-8') as infile:
        md_content = infile.read()

    txt_content = convert_md_to_txt(md_content)
    bbcode_content = convert_md_to_bbcode(md_content)

    with open(txt_output_file, 'w', encoding='utf-8') as txt_outfile:
        txt_outfile.write(txt_content)

    with open(bbcode_output_file, 'w', encoding='utf-8') as bbcode_outfile:
        bbcode_outfile.write(bbcode_content)

# Example usage
input_file = 'README.md'
txt_output_file = 'README.txt'
bbcode_output_file = 'README.bbcode'
convert_readme(input_file, txt_output_file, bbcode_output_file)