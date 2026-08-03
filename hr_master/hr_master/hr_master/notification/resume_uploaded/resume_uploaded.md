<h3>Resume Uploaded</h3>
<p>Dear {{ doc.owner }},</p>
<p>A new resume has been uploaded for candidate <strong>{{ doc.candidate_name }}</strong>.</p>
<p><strong>File:</strong> {{ doc.resume_file }}</p>
<p><strong>Type:</strong> {{ doc.file_type }}</p>
<p><strong>Status:</strong> {{ doc.parsing_status }}</p>
<br>
<p>View Resume: <a href="/app/resume/{{ doc.name }}">{{ doc.name }}</a></p>
