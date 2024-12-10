import random
from flask import Flask, jsonify, request
from firebase_admin import credentials, firestore, initialize_app

# Firebaseの初期化
cred = credentials.Certificate("./key.json")  # サービスアカウントキーへのパスを指定
initialize_app(cred)

db = firestore.client()
rooms_ref = db.collection('rooms')  # Firestoreのroomsコレクションへの参照

app = Flask(__name__)


@app.route('/rooms', methods=['GET'])
def get_rooms():
    try:
        all_rooms = []
        for doc in rooms_ref.stream():
            room_data = doc.to_dict()
            if 'id' in room_data and isinstance(room_data['id'], int):
                all_rooms.append(room_data['id'])
            else:
                print(f"Skipping document without valid id: {doc.id}")

        return jsonify({'rooms': all_rooms}), 200
    except Exception as e:
        print(f"部屋取得に失敗: {e}")
        return jsonify({'message': '500:Internal Server Error.'}), 500


@app.route('/rooms', methods=['POST'])
def create_room():
    try:
        new_id = random.randint(100000, 999999)
        new_room_ref = rooms_ref.add({'id': new_id})
        return jsonify({'id': new_id}), 200

    except Exception as e:
        print(f"部屋作成失敗: {e}")
        return jsonify({'message': '500:内部エラー'}), 500


@app.route('/rooms/<int:room_id>', methods=['DELETE'])
def delete_room(room_id):
    try:
        docs = rooms_ref.where('id', '==', room_id).stream()
        for doc in docs:
            doc.reference.delete()
            return jsonify({'message': f'部屋 {room_id} の削除に成功しました。'}), 200
        return jsonify({'message': f'部屋 {room_id} が見つかりませんでした。'}), 404

    except Exception as e:
        print(f"Error deleting room: {e}")
        return jsonify({'message': '500:内部エラー'}), 500


@app.route('/rooms/<int:room_id>/players', methods=['GET'])
def get_players(room_id):
    try:
        room_ref = rooms_ref.where('id', '==', room_id).get()  # get()ではなくstream()から変更
        if room_ref: # room_refが空でないことを確認
            players = []

            room = next(iter(room_ref), None) # room_refからroomを取得
            if room:
                room_doc = room.to_dict() # roomを辞書に変換

                if 'players' in room_doc and isinstance(room_doc['players'], list): # playersフィールドが存在し、リストであることを確認
                    players = room_doc['players']

                return jsonify({'players': players}), 200


        return jsonify({'message': f'部屋 {room_id} が見つかりませんでした。'}), 404

    except Exception as e:
        print(f"プレイヤー取得エラー: {e}")
        return jsonify({'message': '500:Internal Server Error'}), 500



@app.route('/rooms/<int:room_id>/players', methods=['POST'])
def add_player(room_id):
    try:
        player_id = int(request.args.get('player_id'))
        player_name = request.args.get('player_name')

        room_ref = rooms_ref.where('id', '==', room_id).limit(1).get()

        for doc in room_ref:  # room_idで検索
            doc_ref = rooms_ref.document(doc.id)

            # playersフィールドが存在しない場合、空のリストを作成
            players = doc.to_dict().get('players', [])
            new_player = {
                'id': player_id,
                'name': player_name
            }
            players.append(new_player)

            doc_ref.update({'players': players}) # update players in Firestore

            return jsonify({'message': 'プレイヤーが正常に追加されました'}), 200
        
        return jsonify({'message': f'部屋 {room_id} が見つかりませんでした。'}), 404

    except Exception as e:
        print(f"プレイヤー追加エラー: {e}")
        return jsonify({'message': '500:Internal Server Error'}), 500

@app.route('/rooms/<int:room_id>/players/<int:player_id>', methods=['DELETE'])
def remove_player(room_id, player_id):
    try:
        room_ref = rooms_ref.where('id', '==', room_id).limit(1).get()

        for doc in room_ref:
            doc_ref = rooms_ref.document(doc.id)
            players = doc.to_dict().get('players', [])

            # player_idでプレイヤーを検索し、削除
            updated_players = [player for player in players if player.get('id') != player_id]

            doc_ref.update({'players': updated_players})  # update players in Firestore
            return jsonify({'message': f'プレイヤー {player_id} が部屋 {room_id} から削除されました'}), 200

        return jsonify({'message': f'部屋 {room_id} が見つかりませんでした。'}), 404

    except Exception as e:
        print(f"Error deleting player: {e}")
        return jsonify({'message': '500:Internal Server Error'}), 500



if __name__ == '__main__':
    app.run(debug=True)