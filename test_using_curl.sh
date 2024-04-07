#curl -X POST "http://127.0.0.1:8000/test" \
#    -H "accept: application/json" \
#    -H "Content-Type: application/json" \
#    -d '{"user_email":"test@","institution":"test institution"}'


#curl -X POST "http://127.0.0.1:8000/upload" \
#    -H "Content-Type: multipart/form-data" \
#    -F "data={\"user_email\":\"test@mail.it\",\"institution\":\"test institution\"}" \
#    -F "excel_file=@./Excel_Files/test.xlsx"



curl -X POST "http://127.0.0.1:8000/upload" \
    -H "Content-Type: multipart/form-data" \
    -F "data={\"user_email\":\"test@mail.it\"}" \
    -F "excel_file=@./Excel_Files/test.xlsx"