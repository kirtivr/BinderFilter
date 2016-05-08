/*

BC_REPLY
{(0)(0)(1)(0)%(0)android.intent.action.BATTERY_CHANGED
(0)(0)(0)(255)(255)(16)(0)(255)(255)(255)(255)(05)(05)(05)(05)(05)(05)(05)(05)(254)(255)
(160)(00)BD(12)(0)(10)(0)technology(0)(0)(0)(0)(6)(0)Li-ion(0)(0)(10)(0)icon-small(0)(0)(1)(0)Q(8)(6)(0)health(0)(0)(1)(0)(2)(0)
(20)(0)max_charging_current(0)(0)(1)(0)(0)(0)(6)(0)status(0)(0)(1)(0)(5)(0)(7)(0)plugged(0)(1)(0)(2)(0)(7)(0)present(0)(9)(0)(1)(0)
(5)(0)level(0)(1)(0)d(0)(5)(0)scale(0)(1)(0)d(0)(11)(0)temperature(0)(1)(0)(255)(05)(75)(05)voltage(}

BC_TRANSACTION
{(0)@(30)(0)android.app.IApplicationThread(0)(0)(133)h(127)(07)r(07)(07)(07)
%(07)android.intent.action.BATTERY_CHANGED(07)(07)(07)(255)(255)(16)(0)(255)
(255)(255)(255)(05)(05)(05)(05)(05)(05)(05)(05)(254)(255)(160)(00)
BD(12)(0)(10)(0)technology(0)(0)(0)(0)(6)(0)Li-ion(0)(0)(10)(0)icon-small(0)(0)(1)(0)Q(8)
(6)(0)health(0)(0)(1)(0)(2)(0)(20)(0)max_charging_current(0)(0)(1)(0)(0)(0)
(6)(0)status(0)(0)(1)(0)(5)(0)(7)(0)plugged(0)(1)(0)(2)(0)(7)(0)present(0)(9)(0)(1)(0)
(5)(0)level(0)(1)(0)d(0)}

BC_TRANSACTION
{(0)@(30)(0)android.app.IApplicationThread(0)(0)(133)h(127)(07)(13)(0)(0)(0).(0)
android.bluetooth.adapter.action.STATE_CHANGED(0)(0)(0)(0)(255)(255)(16)(0)(255)(255)(255)(255)(05)(05)(05)
(05)(05)(05)(05)(05)(254)(255)(200)(00)BD(20)(00).(00)android.bluetooth.adapter.extra.PREVIOUS_STATE
(00)(00)(10)(00)(11)(0)%(0)
android.bluetooth.adapter.extra.STATE(0)(1)(0)(12)(0)(255)(255)(255)(255)(255)(255)(05)(05)(05)(05)(255)(255)(35)(05)}

BC_TRANSACTION 
{(0)@(28)(0)android.app.IActivityManager(0)(0)(133)b(127)(07)P(219)`(193)(255)(255)(05)(05)(255)(255)(05)(05)(255)(255)(21)(0)
com.android.bluetooth(0)&(0)com.android.bluetooth.gatt.GattService(0)(0)(0)(0)(0)(0)(0)(0)(0)(0)(254)(255)(228)(08)BD(28)(08)(68)(08)
action(08)(08)(08)(08)4(08)com.android.bluetooth.btservice.action.STATE_CHANGED(08)(08)%(08)
android.bluetooth.adapter.extra.STATE(08)(18)(08)(12)(0)(255)(255)(21)(0)}

BC_REPLY
{(0)(0)(1)(0)(1)(0)(0)(0)(4)(0)WIFI(0)(0)(0)(0)(0)(0)
(9)(0)CONNECTED(0)(9)(0)CONNECTED(0)(0)(0)(1)(0)(0)(0)(255)(255)(18)(0)"Dartmouth Public"(0)(0)}

*/

// ActivityManagerNative.java: http://androidxref.com/6.0.1_r10/xref/frameworks/base/core/java/android/app/ActivityManagerNative.java
public Intent registerReceiver(IApplicationThread caller, String packageName,
        IIntentReceiver receiver,
        IntentFilter filter, String perm, int userId) throws RemoteException
{
    ...
    mRemote.transact(REGISTER_RECEIVER_TRANSACTION, data, reply, 0);
    reply.readException();
    Intent intent = null;
    int haveIntent = reply.readInt();
    if (haveIntent != 0) {
        intent = Intent.CREATOR.createFromParcel(reply);
    }
    ...
    return intent;
}

// Intent.java: http://androidxref.com/6.0.1_r10/xref/frameworks/base/core/java/android/content/Intent.java
private String mAction;
private Uri mData;
private String mType;
private String mPackage;
private ComponentName mComponent;
private int mFlags;
private ArraySet<String> mCategories;
private Bundle mExtras;
private Rect mSourceBounds;
private Intent mSelector;
private ClipData mClipData;

public void readFromParcel(Parcel in) {
    setAction(in.readString());
    mData = Uri.CREATOR.createFromParcel(in);
    mType = in.readString();
    mFlags = in.readInt();
    mPackage = in.readString();
    mComponent = ComponentName.readFromParcel(in);

    if (in.readInt() != 0) {
        mSourceBounds = Rect.CREATOR.createFromParcel(in);
    }

    int N = in.readInt();
    if (N > 0) {
        mCategories = new ArraySet<String>();
        int i;
        for (i=0; i<N; i++) {
            mCategories.add(in.readString().intern());
        }
    } else {
        mCategories = null;
    }

    if (in.readInt() != 0) {
        mSelector = new Intent(in);
    }

    if (in.readInt() != 0) {
        mClipData = new ClipData(in);
    }
    mContentUserHint = in.readInt();
    mExtras = in.readBundle();
}

protected Intent(Parcel in) {
    readFromParcel(in);
}

public Intent setAction(String action) {
    mAction = action != null ? action.intern() : null;
    return this;
}

public int broadcastIntent(IApplicationThread caller,
            Intent intent, String resolvedType, IIntentReceiver resultTo,
            int resultCode, String resultData, Bundle map,
            String[] requiredPermissions, int appOp, Bundle options, boolean serialized,
            boolean sticky, int userId) throws RemoteException
{
    Parcel data = Parcel.obtain();
    Parcel reply = Parcel.obtain();
    data.writeInterfaceToken(IActivityManager.descriptor);
    data.writeStrongBinder(caller != null ? caller.asBinder() : null);
    intent.writeToParcel(data, 0);
    data.writeString(resolvedType);
    data.writeStrongBinder(resultTo != null ? resultTo.asBinder() : null);
    data.writeInt(resultCode);
    data.writeString(resultData);
    data.writeBundle(map);
    data.writeStringArray(requiredPermissions);
    data.writeInt(appOp);
    data.writeBundle(options);
    data.writeInt(serialized ? 1 : 0);
    data.writeInt(sticky ? 1 : 0);
    data.writeInt(userId);
    mRemote.transact(BROADCAST_INTENT_TRANSACTION, data, reply, 0);
    reply.readException();
    int res = reply.readInt();
    reply.recycle();
    data.recycle();
    return res;
}

// Uri.CREATOR.createFromParcel(in) ---------------------------------------------------------------------------------------------------
// Uri.java: http://androidxref.com/6.0.1_r10/xref/frameworks/base/core/java/android/net/Uri.java
private static final int NULL_TYPE_ID = 0;
static final int StringUri.TYPE_ID = 1;
static final int OpaqueUri.TYPE_ID = 2;
static final int HierarchicalUri.TYPE_ID = 3;

public Uri createFromParcel(Parcel in) {
    int type = in.readInt();
    switch (type) {
        case NULL_TYPE_ID: return null;
        case StringUri.TYPE_ID: return StringUri.readFrom(in);
        case OpaqueUri.TYPE_ID: return OpaqueUri.readFrom(in);
        case HierarchicalUri.TYPE_ID:
            return HierarchicalUri.readFrom(in);
    }

    throw new IllegalArgumentException("Unknown URI type: " + type);
}

// StringUri
static Uri readFrom(Parcel parcel) {
    return new StringUri(parcel.readString());
}

// OpaqueUri
static Uri readFrom(Parcel parcel) {
    return new OpaqueUri(
        parcel.readString(),
        Part.readFrom(parcel),
        Part.readFrom(parcel)
    );
}

// HierarchicalUri
 static Uri readFrom(Parcel parcel) {
    return new HierarchicalUri(
        parcel.readString(),
        Part.readFrom(parcel),
        PathPart.readFrom(parcel),
        Part.readFrom(parcel),
        Part.readFrom(parcel)
    );
}

//Part (same as PathPart)
 static Part readFrom(Parcel parcel) {
    int representation = parcel.readInt();
    switch (representation) {
        case Representation.BOTH:
            return from(parcel.readString(), parcel.readString());
        case Representation.ENCODED:
            return fromEncoded(parcel.readString());
        case Representation.DECODED:
            return fromDecoded(parcel.readString());
        default:
            throw new IllegalArgumentException("Unknown representation: "
                    + representation);
    }
}

from(String encoded, String decoded) {
    ...
    return new Part(encoded, decoded);
}


// ComponentName.CREATOR.createFromParcel(in) ---------------------------------------------------------------------------------------------------
// ComponentName.java: http://androidxref.com/6.0.1_r10/xref/frameworks/base/core/java/android/content/ComponentName.java

public static ComponentName readFromParcel(Parcel in) {
    String pkg = in.readString();
    return pkg != null ? new ComponentName(pkg, in) : null;
}

private ComponentName(String pkg, Parcel in) {
    mPackage = pkg;
    mClass = in.readString();
}


// Rect.CREATOR.createFromParcel(in) ---------------------------------------------------------------------------------------------------
// Rect.java: http://androidxref.com/6.0.1_r10/xref/frameworks/base/graphics/java/android/graphics/Rect.java
public void readFromParcel(Parcel in) {
    left = in.readInt();
    top = in.readInt();
    right = in.readInt();
    bottom = in.readInt();
}

// new Clipdata(in) ---------------------------------------------------------------------------------------------------
// ClipData.java: http://androidxref.com/6.0.1_r10/xref/frameworks/base/core/java/android/content/ClipData.java
ClipData(Parcel in) {
    mClipDescription = new ClipDescription(in);
    if (in.readInt() != 0) {
        mIcon = Bitmap.CREATOR.createFromParcel(in);
    } else {
        mIcon = null;
    }
    mItems = new ArrayList<Item>();
    final int N = in.readInt();
    for (int i=0; i<N; i++) {
        CharSequence text = TextUtils.CHAR_SEQUENCE_CREATOR.createFromParcel(in);
        String htmlText = in.readString();
        Intent intent = in.readInt() != 0 ? Intent.CREATOR.createFromParcel(in) : null;
        Uri uri = in.readInt() != 0 ? Uri.CREATOR.createFromParcel(in) : null;
        mItems.add(new Item(text, htmlText, intent, uri));
    }
}


// Parcel.read*() ---------------------------------------------------------------------------------------------------
// java -> http://androidxref.com/6.0.1_r10/xref/frameworks/base/core/java/android/os/Parcel.java
// calls native method -> http://androidxref.com/6.0.1_r10/xref/frameworks/base/core/jni/android_os_Parcel.cpp
// jni layer -> calls cpp method -> http://androidxref.com/6.0.1_r10/xref/frameworks/native/libs/binder/Parcel.cpp


// java
/*Read an integer value from the parcel at the current dataPosition().
    (increases dataPosition() by read_length) */
public final String readString() {
    return nativeReadString(mNativePtr);
}
/*Read an integer value from the parcel at the current dataPosition().
(increases dataPosition() by read_length)*/
public final int readInt() {
    return nativeReadInt(mNativePtr);
}
/*Read and return a new Bundle object from the parcel at the current dataPosition() 
(increases dataPosition() by read_length)*/
public final Bundle readBundle() {
    int length = readInt();
    if (length < 0) {
        if (Bundle.DEBUG) Log.d(TAG, "null bundle: length=" + length);
        return null;
    }
    
    final Bundle bundle = new Bundle(this, length);
    return bundle;
}

// jni
static jstring android_os_Parcel_readString(JNIEnv* env, jclass clazz, jlong nativePtr)
{
    Parcel* parcel = reinterpret_cast<Parcel*>(nativePtr);
    if (parcel != NULL) {
        size_t len;
        const char16_t* str = parcel->readString16Inplace(&len);
        if (str) {
            return env->NewString(reinterpret_cast<const jchar*>(str), len);
        }
        return NULL;
    }
    return NULL;
}

static jint android_os_Parcel_readInt(JNIEnv* env, jclass clazz, jlong nativePtr)
{
    Parcel* parcel = reinterpret_cast<Parcel*>(nativePtr);
    if (parcel != NULL) {
        return parcel->readInt32();
    }
    return 0;
}

// cpp
#define PAD_SIZE_UNSAFE(s) (((s)+3)&~3)

static size_t pad_size(size_t s) {
    if (s > (SIZE_T_MAX - 3)) {
        abort();
    }
    return PAD_SIZE_UNSAFE(s);
}

const char16_t* Parcel::readString16Inplace(size_t* outLen) const
{
    int32_t size = readInt32();
    // watch for potential int overflow from size+1
    if (size >= 0 && size < INT32_MAX) {
        *outLen = size;
        const char16_t* str = (const char16_t*)readInplace((size+1)*sizeof(char16_t));
        if (str != NULL) {
            return str;
        }
    }
    *outLen = 0;
    return NULL;
}

const void* Parcel::readInplace(size_t len) const
{
    if (len > INT32_MAX) {
        // don't accept size_t values which may have come from an
        // inadvertent conversion from a negative int.
        return NULL;
    }

    if ((mDataPos+pad_size(len)) >= mDataPos && (mDataPos+pad_size(len)) <= mDataSize
            && len <= pad_size(len)) {
        const void* data = mData+mDataPos;
        mDataPos += pad_size(len);
        ALOGV("readInplace Setting data pos of %p to %zu", this, mDataPos);
        return data;
    }
    return NULL;
}

int32_t Parcel::readInt32() const
{
    return readAligned<int32_t>();
}

template<class T>
status_t Parcel::readAligned(T *pArg) const {
    COMPILE_TIME_ASSERT_FUNCTION_SCOPE(PAD_SIZE_UNSAFE(sizeof(T)) == sizeof(T));

    if ((mDataPos+sizeof(T)) <= mDataSize) {
        const void* data = mData+mDataPos;
        mDataPos += sizeof(T);
        *pArg =  *reinterpret_cast<const T*>(data);
        return NO_ERROR;
    } else {
        return NOT_ENOUGH_DATA;
    }
}

template<class T>
T Parcel::readAligned() const {
    T result;
    if (readAligned(&result) != NO_ERROR) {
        result = 0;
    }

    return result;
}










