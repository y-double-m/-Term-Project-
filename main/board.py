from main import *
from flask import Blueprint, send_from_directory


blueprint = Blueprint("board", __name__, url_prefix="/board")


@blueprint.route("/upload_image", methods=["POST"])
def upload_image():
    if request.method == "POST":
        file = request.files["image"]
        if file and allowed_file(file.filename):
            filename = "{}.jpg".format(rand_generator())
            savefilepath = os.path.join(app.config["BOARD_IMAGE_PATH"], filename)
            file.save(savefilepath)
            return url_for("board.board_images", filename=filename)


@blueprint.route("/images/<filename>")
def board_images(filename):
    return send_from_directory(app.config["BOARD_IMAGE_PATH"], filename)


@blueprint.route("/list")
def lists():
    # 페이지 값 (값이 없는 경우 기본값 1)
    page = request.args.get("page", 1, type=int)
    # 한페이지당 몇개의 게시물을 출력할지
    limit = request.args.get("limit", 7, type=int)

    search = request.args.get("search", "", type=str)

    # 최종적으로 완성된 query를 만들 변수
    query = {}
    # 검색어 상태를 추가할 리스트 변수
    search_list = []

    search_list.append({"keyword": {"$regex": search}})
    

    # 검색 대상이 한개라도 존재할 경우 query 변수에 $or 리스트를 쿼리 합니다.
    if len(search_list) > 0:
        query = {"$or": search_list}


    board = mongo.db.board
    datas = board.find(query).skip((page - 1) * limit).limit(limit).sort("pubdate", -1)

    # 게시물의 총 갯수
    tot_count = board.count_documents(query)
    # 마지막 페이지의 수를 구합니다
    last_page_num = math.ceil(tot_count / limit)

    # 페이지 블럭을 5개씩 표기
    block_size = 5
    # 현재 블럭의 위치
    block_num = int((page - 1) / block_size)
    # 블럭의 시작 위치
    block_start = int((block_size * block_num) + 1)
    # 블럭의 끝 위치
    block_last = math.ceil(block_start + (block_size - 1))

    return render_template(
        "list.html",
        datas=list(datas),
        limit=limit,
        page=page,
        block_start=block_start,
        block_last=block_last,
        last_page_num=last_page_num,
        search=search,
        title="판매물품 리스트")


@blueprint.route("/view/<idx>") # 게시판 상세보기
def board_view(idx):
    if idx is not None:
        page = request.args.get("page")
        search = request.args.get("search")

        board = mongo.db.board
        data = board.find_one({"_id": ObjectId(idx)})

        if data is not None:
            result = {
                "id": data.get("_id"),
                "name": data.get("name"),
                "title": data.get("title"),
                "keyword": data.get("keyword"),
                "contents": data.get("contents"),
                "pubdate": data.get("pubdate"),
                "state": data.get("state"),
                "writer_id": data.get("writer_id", "")
            }

            return render_template("view.html", result=result, page=page, search=search, title="글 상세보기")
    return abort(404)


@blueprint.route("/write", methods=["GET", "POST"]) # 게시판 글쓰기
@login_required
def board_write():
    if request.method == "POST":
        
        name = request.form.get("name")
        title = request.form.get("title")
        contents = request.form.get("contents")
        keyword = request.form.get("keyword")
        state = request.form.get("state")
       
        cur_utc_time = round(datetime.utcnow().timestamp() * 1000)
        board = mongo.db.board # board 테이블 생성
        post = {
            "name": name,
            "title": title,
            "keyword": keyword,
            "contents": contents,
            "pubdate": cur_utc_time,
            "state": state,
            "writer_id": session.get("id"),
        }

        x = board.insert_one(post)
        print(x.inserted_id)
        return redirect(url_for("board.board_view", idx=x.inserted_id))
    else:
        return render_template("write.html", title="글 작성")


@blueprint.route("/edit/<idx>", methods=["GET", "POST"])
def board_edit(idx):
    if request.method == "GET":
        board = mongo.db.board
        data = board.find_one({"_id": ObjectId(idx)})
        if data is None:
            flash("해당 게시물이 존재하지 않습니다.")
            return redirect(url_for("board.lists"))
        else:
            if session.get("id") == data.get("writer_id"):
                return render_template("edit.html", data=data, title="글 수정")
            else:
                flash("글 수정 권한이 없습니다.")
                return redirect(url_for("board.lists"))
    else:
        title = request.form.get("title")
        contents = request.form.get("contents")
        keyword = request.form.get("keyword")
        state = request.form.get("state")

        board = mongo.db.board
        data = board.find_one({"_id": ObjectId(idx)})
        if session.get("id") == data.get("writer_id"):
            board.update_one({"_id": ObjectId(idx)}, {
                "$set": {
                    "title": title,
                    "keyword": keyword,
                    "contents": contents,
                    "state": state
                }
            })
            flash("수정되었습니다.")
            return redirect(url_for("board.board_view", idx=idx))
        else:
            flash("글 수정 권한이 없습니다.")
            return redirect(url_for("board.lists"))


@blueprint.route("/delete/<idx>")
def board_delete(idx):
    board = mongo.db.board
    data = board.find_one({"_id": ObjectId(idx)})
    if data.get("writer_id") == session.get("id"):
        board.delete_one({"_id": ObjectId(idx)})
        flash("삭제되었습니다.")
    else:
        flash("삭제 권한이 없습니다.")
    return redirect(url_for("board.lists"))