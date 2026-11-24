const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, WidthType,
  AlignmentType, BorderStyle, ShadingType, Header, Footer, PageNumber,
} = require('docx');

const OUT = '/mnt/user-data/outputs/loan_app_templates';
fs.mkdirSync(OUT, { recursive: true });

const FONT = 'Times New Roman';
const W = 9360; // letter, 1" margins

// ---------- helpers ----------
function run(t, o = {}) {
  return new TextRun({ text: t, font: FONT, size: o.size || 22, bold: o.bold, italics: o.italics, color: o.color });
}
// content: string | array of (string | [string, opts])
function para(content, o = {}) {
  const parts = typeof content === 'string' ? [content] : content;
  const runs = parts.map(c => (typeof c === 'string' ? run(c, o) : run(c[0], { ...o, ...c[1] })));
  return new Paragraph({
    children: runs,
    alignment: o.align,
    spacing: { before: o.before || 0, after: o.after === undefined ? 120 : o.after },
    indent: o.indent,
    keepNext: o.keepNext,
    border: o.border,
    pageBreakBefore: o.pageBreakBefore,
  });
}
const title = (t, sub) => [
  para(t, { align: AlignmentType.CENTER, bold: true, size: 30, after: sub ? 40 : 200 }),
  ...(sub ? [para(sub, { align: AlignmentType.CENTER, italics: true, size: 20, after: 200 })] : []),
];
const heading = t => para(t, { bold: true, size: 23, before: 200, after: 80, keepNext: true });
const body = (t, o = {}) => para(t, { align: AlignmentType.JUSTIFIED, ...o });
const clause = (num, t, o = {}) =>
  para([[num + '  ', { bold: true }], ...(Array.isArray(t) ? t : [t])], { align: AlignmentType.JUSTIFIED, indent: { left: 540, hanging: 540 }, ...o });
const note = t => para(t, { italics: true, size: 20, color: '7A4B00', indent: { left: 540 } });
const tag = t => para(t, { size: 14, after: 0 }); // docxtpl control paragraph (removed on render)

const hair = { style: BorderStyle.SINGLE, size: 4, color: '808080' };
const boxed = { top: hair, bottom: hair, left: hair, right: hair };
const none = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
const noBorders = { top: none, bottom: none, left: none, right: none };

function cell(content, w, o = {}) {
  const kids = (Array.isArray(content) ? content : [content]).map(c =>
    typeof c === 'string' ? para(c, { after: 0, size: o.size, bold: o.bold, align: o.align }) : c);
  return new TableCell({
    width: { size: w, type: WidthType.DXA },
    borders: o.noBorder ? noBorders : boxed,
    shading: o.fill ? { fill: o.fill, type: ShadingType.CLEAR, color: 'auto' } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: kids,
  });
}
function table(widths, rows) {
  return new Table({
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    columnWidths: widths,
    rows,
  });
}
function kv(rows, w1 = 4900, w2 = W - 4900) {
  return table([w1, w2], rows.map(([k, v]) =>
    new TableRow({ children: [cell(k, w1, { fill: 'F2F2F2', bold: true }), cell(v, w2)] })));
}

function sigBlock(leftName, leftRole, rightName, rightRole) {
  const half = W / 2;
  const sig = (name, role) => [
    para('', { before: 520, after: 0 }),
    para(name, { align: AlignmentType.CENTER, bold: true, after: 0,
      border: { top: { style: BorderStyle.SINGLE, size: 6, color: '000000', space: 2 } } }),
    para(role, { align: AlignmentType.CENTER, size: 20, after: 0 }),
  ];
  return table([half, half], [new TableRow({
    cantSplit: true,
    children: [cell(sig(leftName, leftRole), half, { noBorder: true }), cell(sig(rightName, rightRole), half, { noBorder: true })],
  })]);
}

function makeDoc(children, { initials = true } = {}) {
  const footerKids = [];
  if (initials) {
    footerKids.push(para('Initials:   Lender ________     Borrower ________', { align: AlignmentType.CENTER, size: 18, after: 40 }));
  }
  footerKids.push(new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [
      new TextRun({ text: 'Prepared with software. Not legal advice. Not notarized.     Page ', font: FONT, size: 16, color: '555555' }),
      new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: '555555' }),
      new TextRun({ text: ' of ', font: FONT, size: 16, color: '555555' }),
      new TextRun({ children: [PageNumber.TOTAL_PAGES], font: FONT, size: 16, color: '555555' }),
    ],
  }));
  return new Document({
    creator: 'Loan App',
    styles: { default: { document: { run: { font: FONT, size: 22 } } } },
    sections: [{
      properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1300, left: 1440 } } },
      headers: { default: new Header({ children: [
        para('{{ draft_banner }}', { align: AlignmentType.CENTER, bold: true, size: 18, color: 'B00020', after: 0 }),
        para('Loan {{ loan_ref }}  \u00B7  Version {{ version_no }}', { align: AlignmentType.CENTER, size: 16, color: '555555', after: 0 }),
      ] }) },
      footers: { default: new Footer({ children: footerKids }) },
      children,
    }],
  });
}
async function save(name, doc) {
  fs.writeFileSync(`${OUT}/${name}`, await Packer.toBuffer(doc));
  console.log('wrote', name);
}

// shared party block
const parties = () => [
  para([['LENDER: ', { bold: true }], '{{ lender_name }}, of legal age, {{ lender_citizenship }}, {{ lender_civil_status }}, residing at {{ lender_address }} (the \u201CLender\u201D); and'], { align: AlignmentType.JUSTIFIED }),
  para([['BORROWER: ', { bold: true }], '{{ borrower_name }}, of legal age, {{ borrower_citizenship }}, {{ borrower_civil_status }}, residing at {{ borrower_address }} (the \u201CBorrower\u201D).'], { align: AlignmentType.JUSTIFIED }),
];

(async () => {
  // ================= 1. DISCLOSURE =================
  {
    const rows = [
      ['Amount financed (principal)', '{{ amount_financed }}'],
      ['Finance charge in pesos and centavos (total interest and charges over the full term)', '{{ finance_charge }}'],
      ['Finance charge as a simple annual rate on the unpaid balance', '{{ simple_annual }}% per annum  ({{ monthly_rate }}% per month)'],
      ['Total of payments (amount financed + finance charge)', '{{ total_payable }}'],
      ['Number of payments', '{{ term_months }} monthly installments'],
      ['Regular installment', '{{ payment }}'],
      ['Final installment', '{{ final_payment }}'],
      ['First and last due dates', '{{ first_due_date }}  to  {{ last_due_date }}'],
      ['Late charge', '{{ late_charge_text }}'],
      ['Other fees or charges', '{{ other_charges_text }}'],
      ['Documentary stamp tax (estimate only) and who bears it', '{{ dst_estimate }}  \u2014  {{ dst_payer }}'],
      ['For comparison only: effective annual rate if interest is compounded monthly', '{{ effective_annual }}%'],
    ];
    const kids = [
      ...title('DISCLOSURE STATEMENT', 'Cost of credit and loan terms \u2014 to be given to the Borrower before signing'),
      kv([['Date of this statement', '{{ disclosure_date }}'], ['Lender', '{{ lender_name }}'], ['Borrower', '{{ borrower_name }}'], ['Loan reference', '{{ loan_ref }}, Version {{ version_no }}']], 3000, W - 3000),
      heading('A.  Key terms'),
      kv(rows),
      tag('{%p if path == \'EXISTING\' %}'),
      heading('B.  Existing balance being restructured'),
      kv([
        ['Statement as of', '{{ as_of_date }}'],
        ['Outstanding principal confirmed by the Lender', '{{ opening_balance }}'],
        ['Agreed adjustment', '{{ adjustment_fmt }}'],
        ['Unpaid amounts carried into the principal', '{{ arrears_fmt }}'],
        ['New principal under the restructured loan', '{{ amount_financed }}'],
        ['Previous arrangement', '{{ prior_arrangement_text }}'],
      ]),
      tag('{%p endif %}'),
      heading('C.  How the loan works'),
      clause('1.', [['Interest. ', { bold: true }], '{{ rule_interest_method }}']),
      clause('2.', [['Rounding. ', { bold: true }], '{{ rule_rounding }}']),
      clause('3.', [['Due dates. ', { bold: true }], '{{ rule_short_month }}']),
      clause('4.', [['How payments are applied. ', { bold: true }], '{{ rule_application }}']),
      clause('5.', [['Prepayment. ', { bold: true }], '{{ rule_prepayment }}']),
      clause('6.', [['Where payments are made. ', { bold: true }], '{{ rule_place_of_payment }}']),
      clause('7.', [['Payment schedule. ', { bold: true }], 'Every installment is listed in Annex A (Amortization Schedule). The figures in this statement, Annex A, and the Loan Agreement come from the same calculation and must match.']),
      note('[DRAFTING NOTE \u2014 LAWYER: confirm required disclosure items and format under the Truth in Lending Act and its implementing rules, if applicable to this lender.]'),
      heading('D.  Borrower\u2019s receipt'),
      body('I received a copy of this Disclosure Statement on ____________________ (date), before signing the loan documents, and I had the chance to ask questions about it.'),
      sigBlock('{{ borrower_name }}', 'Borrower', '{{ lender_name }}', 'Lender'),
    ];
    await save('01_disclosure_statement.docx', makeDoc(kids));
  }

  // ================= 2. AMORTIZATION SCHEDULE (ANNEX A) =================
  {
    const cw = [700, 1620, 1500, 1300, 1400, 1440, 1400]; // 9360
    const hdr = ['No.', 'Due date', 'Opening balance', 'Interest', 'Principal', 'Installment', 'Closing balance'];
    const right = AlignmentType.RIGHT;
    const loopRow = (txt) => new TableRow({ children: cw.map((w, i) => cell(i === 0 ? txt : '', w, { size: 12 })) });
    const dataRow = new TableRow({
      children: [
        cell('{{ r.seq }}', cw[0], { align: AlignmentType.CENTER, size: 19 }),
        cell('{{ r.due_date }}', cw[1], { size: 19 }),
        cell('{{ r.opening }}', cw[2], { align: right, size: 19 }),
        cell('{{ r.interest }}', cw[3], { align: right, size: 19 }),
        cell('{{ r.principal }}', cw[4], { align: right, size: 19 }),
        cell('{{ r.payment }}', cw[5], { align: right, size: 19 }),
        cell('{{ r.closing }}', cw[6], { align: right, size: 19 }),
      ],
    });
    const tbl = table(cw, [
      new TableRow({ tableHeader: true, children: hdr.map((h, i) => cell(h, cw[i], { fill: 'D9D9D9', bold: true, size: 19, align: AlignmentType.CENTER })) }),
      loopRow('{%tr for r in schedule %}'),
      dataRow,
      loopRow('{%tr endfor %}'),
      new TableRow({ children: [
        cell('', cw[0], { fill: 'F2F2F2' }),
        cell('TOTAL', cw[1], { fill: 'F2F2F2', bold: true, size: 19 }),
        cell('', cw[2], { fill: 'F2F2F2' }),
        cell('{{ total_interest_plain }}', cw[3], { fill: 'F2F2F2', bold: true, size: 19, align: right }),
        cell('{{ total_principal_plain }}', cw[4], { fill: 'F2F2F2', bold: true, size: 19, align: right }),
        cell('{{ total_payable_plain }}', cw[5], { fill: 'F2F2F2', bold: true, size: 19, align: right }),
        cell('', cw[6], { fill: 'F2F2F2' }),
      ] }),
    ]);
    const kids = [
      ...title('ANNEX A \u2014 AMORTIZATION SCHEDULE', 'Part of the Loan Agreement and Promissory Note for loan {{ loan_ref }}'),
      kv([
        ['Borrower', '{{ borrower_name }}'],
        ['Lender', '{{ lender_name }}'],
        ['Principal', '{{ principal }}'],
        ['Interest rate', '{{ monthly_rate }}% per month ({{ simple_annual }}% per annum, simple)'],
        ['Term / due day', '{{ term_months }} months; due on day {{ due_day }} of each month'],
      ], 2600, W - 2600),
      para('', { after: 120 }),
      tbl,
      para('All amounts are in Philippine pesos (PHP).', { size: 18, italics: true, before: 80 }),
      heading('How to read this schedule'),
      clause('1.', '{{ rule_interest_method }}', { size: 20 }),
      clause('2.', '{{ rule_rounding }}', { size: 20 }),
      clause('3.', '{{ rule_short_month }}', { size: 20 }),
      clause('4.', '{{ rule_application }}', { size: 20 }),
      clause('5.', '{{ rule_records }}', { size: 20 }),
    ];
    await save('02_amortization_schedule_annex_a.docx', makeDoc(kids));
  }

  // ================= 3. LOAN AGREEMENT =================
  {
    const kids = [
      ...title('{{ agreement_title }}'),
      body('This {{ agreement_title }} (the \u201CAgreement\u201D) is made on {{ doc_date }} at {{ place_of_signing }}, between:'),
      ...parties(),
      heading('Background'),
      tag('{%p if path == \'EXISTING\' %}'),
      body('The Lender has previously lent money to the Borrower. Until now the Borrower has been paying under this arrangement: {{ prior_arrangement_text }}. The parties now want to put the debt on clear written terms, with scheduled payments of both principal and interest, as stated below.'),
      tag('{%p else %}'),
      body('The Borrower asked the Lender for a loan, and the Lender agreed to lend on the terms stated below.'),
      tag('{%p endif %}'),
      body('The parties therefore agree:'),

      heading('1.  The Loan'),
      tag('{%p if path == \'EXISTING\' %}'),
      clause('1.1', 'The Borrower confirms that as of {{ as_of_date }} the Borrower owes the Lender {{ principal_words }} ({{ principal }}) (the \u201CPrincipal\u201D), made up of: outstanding principal of {{ opening_balance }}; agreed adjustment of {{ adjustment_fmt }}; and unpaid amounts carried into the Principal of {{ arrears_fmt }}.'),
      clause('1.2', 'From the first due date in Section 3, this Agreement replaces the earlier arrangement described in the Background.'),
      note('[DRAFTING NOTE \u2014 LAWYER: confirm how the earlier arrangement is ended, and how interest already paid is treated in the Principal.]'),
      tag('{%p else %}'),
      clause('1.1', 'The Lender lends and the Borrower borrows {{ principal_words }} ({{ principal }}) (the \u201CPrincipal\u201D). The Borrower acknowledges receiving the Principal in full on {{ disbursement_date }}.'),
      tag('{%p endif %}'),

      heading('2.  Interest'),
      clause('2.1', 'The Principal bears interest at {{ monthly_rate }}% per month ({{ simple_annual }}% per annum, simple).'),
      clause('2.2', '{{ rule_interest_method }}'),
      clause('2.3', '{{ rule_rounding }}'),

      heading('3.  Repayment'),
      clause('3.1', 'The Borrower shall pay the Principal and interest in {{ term_months }} monthly installments of {{ payment }} each, except the final installment of {{ final_payment }}, as listed in the Amortization Schedule attached as Annex A.'),
      clause('3.2', 'The first installment is due on {{ first_due_date }} and the last on {{ last_due_date }}.'),
      clause('3.3', '{{ rule_short_month }}'),
      clause('3.4', 'If all installments are paid on schedule, the Borrower will have paid {{ total_payable }} in total, of which {{ total_interest }} is interest.'),

      heading('4.  Payments, Receipts and Records'),
      clause('4.1', '{{ rule_place_of_payment }}'),
      clause('4.2', '{{ rule_application }}'),
      clause('4.3', '{{ rule_records }}'),

      heading('5.  Prepayment'),
      clause('5.1', '{{ rule_prepayment }}'),

      heading('6.  Late Payment'),
      clause('6.1', '{{ late_charge_text }}'),

      heading('7.  Default'),
      clause('7.1', 'If the Borrower does not pay an installment within ______ days after its due date, the Lender may give the Borrower written notice to pay. If the amount due is still unpaid ______ days after the notice, the Lender may declare the unpaid Principal and accrued interest due, to the extent the law allows.'),
      note('[DRAFTING NOTE \u2014 LAWYER AND LENDER: fill the blanks and confirm this clause. The software does not supply collection actions or threats, and none should be added here.]'),

      heading('8.  Disclosure'),
      clause('8.1', 'The Borrower confirms receiving the Disclosure Statement dated {{ disclosure_date }} before signing this Agreement, and that its figures match this Agreement and Annex A.'),

      heading('9.  Taxes and Costs'),
      clause('9.1', 'Documentary stamp tax and notarial fees (if any) are for the account of {{ dst_payer }}. The documentary stamp tax is estimated at {{ dst_estimate }}.'),

      tag('{%p if with_promissory_note %}'),
      heading('10.  Promissory Note'),
      clause('10.1', 'The Borrower is also signing a Promissory Note for this loan. The Note and this Agreement describe the same debt; the Borrower owes the amount only once.'),
      tag('{%p endif %}'),

      heading('11.  Changes'),
      clause('11.1', 'Any change in the terms of this Agreement must be in writing, signed by both parties, and issued as a new version of the loan. Earlier signed versions are kept as part of the record.'),

      heading('12.  General'),
      clause('12.1', 'Philippine law governs this Agreement. Any court case shall be filed in ______________________________.'),
      clause('12.2', 'If any part of this Agreement is found unenforceable, the rest remains in effect. This Agreement, with Annex A and the Disclosure Statement, is the whole agreement of the parties on this loan.'),
      clause('12.3', 'Each party has read and understood this Agreement and has had the chance to consult a lawyer before signing.'),
      note('[DRAFTING NOTE \u2014 LAWYER: confirm governing-law and venue wording, and whether spousal consent or other clauses are needed.]'),

      heading('13.  Notice About This Document'),
      clause('13.1', 'This document was prepared with software to organize the loan terms. It is not legal advice and has not been notarized. Notarization, if desired, is done by a notary public before whom the parties personally appear.', { keepNext: true }),

      para('IN WITNESS WHEREOF, the parties sign this Agreement on {{ doc_date }} at {{ place_of_signing }}.', { before: 240, keepNext: true, align: AlignmentType.JUSTIFIED }),
      sigBlock('{{ lender_name }}', 'Lender', '{{ borrower_name }}', 'Borrower'),
      para('', { after: 60 }),
      para('Signed in the presence of:', { keepNext: true, before: 120 }),
      sigBlock('{{ witness1_name }}', 'Witness', '{{ witness2_name }}', 'Witness'),
      para('Annexes:  A \u2014 Amortization Schedule;  B \u2014 Disclosure Statement.', { before: 200, size: 20 }),
      para('An acknowledgment page for the notary follows on a separate sheet.', { size: 20, italics: true }),
    ];
    await save('03_loan_agreement.docx', makeDoc(kids));
  }

  // ================= 4. PROMISSORY NOTE =================
  {
    const kids = [
      ...title('PROMISSORY NOTE'),
      kv([['Principal amount', '{{ principal }}'], ['Date and place', '{{ doc_date }}, {{ place_of_signing }}'], ['Loan reference', '{{ loan_ref }}, Version {{ version_no }}']], 3000, W - 3000),
      para('', { after: 120 }),
      body([['FOR VALUE RECEIVED', { bold: true }], '{% if path == \'EXISTING\' %}, and in restructuring of an existing debt,{% endif %} I, {{ borrower_name }}, of legal age, {{ borrower_citizenship }}, {{ borrower_civil_status }}, residing at {{ borrower_address }} (the \u201CBorrower\u201D), promise to pay {{ lender_name }}, of {{ lender_address }} (the \u201CLender\u201D), or order, the principal sum of {{ principal_words }} ({{ principal }}), with interest at {{ monthly_rate }}% per month ({{ simple_annual }}% per annum, simple), as follows:']),
      clause('1.', [['Installments. ', { bold: true }], '{{ term_months }} monthly installments of {{ payment }} each, except the final installment of {{ final_payment }}, from {{ first_due_date }} until {{ last_due_date }}, as listed in the Amortization Schedule attached as Annex A.']),
      clause('2.', [['Interest. ', { bold: true }], '{{ rule_interest_method }}']),
      clause('3.', [['Rounding. ', { bold: true }], '{{ rule_rounding }}']),
      clause('4.', [['Due dates. ', { bold: true }], '{{ rule_short_month }}']),
      clause('5.', [['Application of payments. ', { bold: true }], '{{ rule_application }}']),
      clause('6.', [['Place of payment and receipts. ', { bold: true }], '{{ rule_place_of_payment }}']),
      clause('7.', [['Prepayment. ', { bold: true }], '{{ rule_prepayment }}']),
      clause('8.', [['Late payment. ', { bold: true }], '{{ late_charge_text }}']),
      clause('9.', [['Default. ', { bold: true }], 'If I do not pay an installment within ______ days after its due date, the Lender may give me written notice to pay. If the amount due is still unpaid ______ days after the notice, the Lender may declare the unpaid principal and accrued interest due, to the extent the law allows.']),
      note('[DRAFTING NOTE \u2014 LAWYER AND LENDER: fill the blanks; decide whether any waiver of presentment, demand, or notice is wanted. None is included.]'),
      tag('{%p if with_loan_agreement %}'),
      clause('10.', [['Same debt. ', { bold: true }], 'This Note is issued for the same loan described in the Loan Agreement of {{ doc_date }}. The Note and the Agreement describe one debt, and I owe the amount only once.']),
      tag('{%p endif %}'),
      clause('11.', [['Record of payments. ', { bold: true }], '{{ rule_records }}']),
      body('This Note is governed by Philippine law. This document was prepared with software, is not legal advice, and has not been notarized.', { size: 20, before: 120, keepNext: true }),
      para('SIGNED on {{ doc_date }} at {{ place_of_signing }}.', { before: 200, keepNext: true }),
      sigBlock('{{ borrower_name }}', 'Borrower (Maker)', '{{ lender_name }}', 'Lender (Payee)'),
      para('', { after: 60 }),
      para('Signed in the presence of:', { keepNext: true, before: 120 }),
      sigBlock('{{ witness1_name }}', 'Witness', '{{ witness2_name }}', 'Witness'),
      para('Annex A \u2014 Amortization Schedule is attached. An acknowledgment page for the notary follows on a separate sheet.', { before: 200, size: 20, italics: true }),
    ];
    await save('04_promissory_note.docx', makeDoc(kids));
  }

  // ================= 5. NOTARIAL ACKNOWLEDGMENT PAGE =================
  {
    const cw = [3300, 3300, 2760];
    const blank = '______________________';
    const kids = [
      para('NOTARY TO COMPLETE. The software fills in only the names and the title of the document. It does not fill in, sign, or certify any notarial entry, and it does not notarize.', {
        italics: true, size: 19, color: '7A4B00', align: AlignmentType.CENTER, after: 280 }),
      ...title('ACKNOWLEDGMENT'),
      para('REPUBLIC OF THE PHILIPPINES      )', { after: 0 }),
      para('________________________________      )  S.S.', { after: 240 }),
      body('BEFORE ME, a Notary Public for and in ____________________________, this _____ day of ____________________, 20____, personally appeared:', { after: 160 }),
      table(cw, [
        new TableRow({ children: ['Name', 'Competent Evidence of Identity', 'Date and Place Issued'].map((h, i) => cell(h, cw[i], { fill: 'D9D9D9', bold: true, size: 20, align: AlignmentType.CENTER })) }),
        new TableRow({ children: [cell('{{ lender_name }}', cw[0]), cell(blank, cw[1]), cell(blank, cw[2])] }),
        new TableRow({ children: [cell('{{ borrower_name }}', cw[0]), cell(blank, cw[1]), cell(blank, cw[2])] }),
      ]),
      para('', { after: 120 }),
      body('who are known to me, or whom I identified through the competent evidence of identity stated above, to be the same persons who executed the foregoing instrument, the {{ ack_document_title }}, consisting of _____ pages including this page and the annexes, and they acknowledged to me that the same is their free and voluntary act and deed.'),
      body('WITNESS MY HAND AND SEAL on the date and at the place first written above.', { before: 120, after: 480 }),
      para('________________________________', { align: AlignmentType.RIGHT, after: 0 }),
      para('NOTARY PUBLIC', { align: AlignmentType.RIGHT, bold: true, after: 0 }),
      para('Until ____________________   Commission No. ____________', { align: AlignmentType.RIGHT, size: 20, after: 0 }),
      para('Roll No. ______   IBP No. ______   PTR No. ______   MCLE Compliance No. ______', { align: AlignmentType.RIGHT, size: 20, after: 360 }),
      para('Doc. No. ________;', { after: 0 }),
      para('Page No. ________;', { after: 0 }),
      para('Book No. ________;', { after: 0 }),
      para('Series of 20____.', { after: 240 }),
      note('[DRAFTING NOTE \u2014 LAWYER: confirm the acknowledgment form and the identity-document wording against the notarial rules now in force, including the March 2025 amendments. The notary may use his or her own form.]'),
    ];
    await save('05_notarial_acknowledgment_page.docx', makeDoc(kids, { initials: false }));
  }
})();
